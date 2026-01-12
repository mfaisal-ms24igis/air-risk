# Celery → Django-Q Migration Plan

**Status**: Ready to execute  
**Reason**: Eliminate duplication - Django-Q is simpler (no Redis broker needed, uses PostgreSQL ORM)

---

## Current Situation

**Problem**: Both Celery AND Django-Q are configured, causing:
- Duplicate task execution risk
- Resource waste (Redis only needed for Celery)
- Configuration complexity
- Maintenance overhead

**Evidence**:
- `celery_worker` and `celery_beat` containers in docker-compose.yml
- Django-Q configured in settings with PostgreSQL ORM broker
- `@shared_task` decorators in code (Celery style)
- Both systems running concurrently

---

## Migration Strategy

### Why Django-Q?

✅ **Simpler**: No separate broker needed (uses PostgreSQL)  
✅ **Lighter**: Fewer dependencies  
✅ **Integrated**: Better Django integration  
✅ **Sufficient**: Meets all current requirements  
✅ **Active**: Well-maintained for Django projects  

### Tasks to Migrate

All current Celery tasks will be converted to Django-Q:

#### air_quality/tasks.py
- `run_daily_ingestion_pipeline` → Django-Q scheduled task
- `cleanup_old_rasters` → Django-Q scheduled task

#### correction/tasks.py
- `retrain_all_models` → Django-Q scheduled task
- Various model training tasks

#### exposure/tasks.py
- Exposure calculation tasks
- Hotspot detection tasks

#### reports/tasks.py
- `generate_scheduled_reports` → Django-Q scheduled task
- Report generation tasks

---

## Implementation Steps

### 1. Update Task Decorators

**Before** (Celery):
```python
from celery import shared_task

@shared_task(bind=True, queue="gis", max_retries=2)
def process_data(self, data_id):
    # ...
```

**After** (Django-Q):
```python
from django_q.tasks import async_task, schedule

def process_data(data_id):
    # No decorator needed - called via async_task()
    # ...

# Usage:
task_id = async_task('air_quality.tasks.process_data', data_id)
```

### 2. Convert Scheduled Tasks

**Before** (Celery Beat in celery.py):
```python
app.conf.beat_schedule = {
    "fetch-and-process-daily-pipeline": {
        "task": "air_quality.tasks.run_daily_ingestion_pipeline",
        "schedule": crontab(hour=6, minute=0),
    },
}
```

**After** (Django-Q Schedule in database):
```python
from django_q.models import Schedule

Schedule.objects.create(
    func='air_quality.tasks.run_daily_ingestion_pipeline',
    schedule_type=Schedule.CRON,
    cron='0 6 * * *',  # Daily at 06:00 UTC
    name='Daily Ingestion Pipeline',
)
```

### 3. Remove Celery Configuration

Files to modify:
- `air_risk/celery.py` → Delete or archive
- `air_risk/__init__.py` → Remove Celery app import
- `docker-compose.yml` → Remove celery_worker & celery_beat services
- `settings/base.py` → Remove CELERY_* settings
- `requirements/base.txt` → Remove celery, django-celery-beat

### 4. Keep Redis (Optional)

Redis can still be used for:
- Django caching (already configured)
- Session storage (optional)
- WebSocket backend (if needed in future)

---

## Changes Required

### Files to Modify

1. **air_risk/__init__.py**
   - Remove Celery app initialization

2. **air_risk/settings/base.py**
   - Remove CELERY_* configuration
   - Keep Q_CLUSTER configuration

3. **docker-compose.yml**
   - Remove `celery_worker` service
   - Remove `celery_beat` service
   - Keep `redis` (used for caching)

4. **requirements/base.txt**
   - Remove `celery>=5.3,<6.0`
   - Remove `django-celery-beat>=2.5,<3.0`
   - Keep `django-q2>=1.6,<2.0`

5. **Task files** (*.tasks.py)
   - Convert `@shared_task` to plain functions
   - Update task invocation to use `async_task()`

6. **Management command** (create new)
   - `management/commands/setup_schedules.py`
   - Initialize Django-Q schedules

---

## Testing Plan

### Before Migration
```bash
# Document current scheduled tasks
python manage.py shell
>>> from django_celery_beat.models import PeriodicTask
>>> list(PeriodicTask.objects.values_list('name', 'task'))

# Test current task execution
celery -A air_risk inspect active
```

### After Migration
```bash
# Verify Django-Q cluster starts
python manage.py qcluster

# Check scheduled tasks
python manage.py shell
>>> from django_q.models import Schedule
>>> list(Schedule.objects.values_list('name', 'func'))

# Test task execution
python manage.py shell
>>> from django_q.tasks import async_task
>>> task_id = async_task('air_quality.tasks.test_task')
```

---

## Rollback Plan

If issues arise:

1. **Restore Celery services** in docker-compose.yml
2. **Reinstall Celery**: `pip install celery django-celery-beat`
3. **Revert code changes** from git
4. **Restart services**: `docker-compose up -d`

---

## Benefits After Migration

| Aspect | Before (Dual) | After (Django-Q only) |
|--------|--------------|----------------------|
| **Containers** | 7 (web, db, redis, celery_worker, celery_beat, geoserver) | 5 (remove 2 celery) |
| **Dependencies** | Celery + Django-Q | Django-Q only |
| **Broker** | Redis (Celery) + PostgreSQL (Django-Q) | PostgreSQL only |
| **Configuration** | 2 task systems | 1 task system |
| **Memory** | ~400 MB | ~250 MB |
| **Complexity** | High | Low |

---

## Migration Timeline

**Estimated Time**: 2-3 hours

1. **Preparation** (30 min)
   - Backup database
   - Document current schedules
   - Test current tasks

2. **Code Changes** (60 min)
   - Convert task decorators
   - Create schedule setup command
   - Update settings

3. **Infrastructure** (30 min)
   - Update docker-compose.yml
   - Update requirements.txt
   - Rebuild containers

4. **Testing** (30 min)
   - Verify Django-Q cluster
   - Test task execution
   - Verify schedules

---

## Post-Migration Monitoring

Monitor for:
- Task execution success rate
- Scheduled task completion
- PostgreSQL connection pool usage
- Memory usage (should decrease)

---

**Ready to proceed?** The migration is straightforward and will significantly simplify the architecture.
