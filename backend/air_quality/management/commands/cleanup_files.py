"""
Management command to clean up loose files in the workspace.

Moves runtime-generated files (CSVs, SHPs, logs, etc.) to the
processed_data directory for organization.

Usage:
    python manage.py cleanup_files --dry-run  # Preview what would be moved
    python manage.py cleanup_files            # Actually move files
"""

from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings

from air_quality.api.utils import FileHygiene


class Command(BaseCommand):
    help = "Clean up loose files by moving them to processed_data directory"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what files would be moved without actually moving them",
        )
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Scan subdirectories recursively",
        )
        parser.add_argument(
            "--directory",
            type=str,
            default=None,
            help="Specific directory to scan (default: project root)",
        )

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        recursive = options["recursive"]
        directory = options.get("directory") or settings.BASE_DIR

        self.stdout.write(
            self.style.NOTICE(f"\n{'=' * 60}")
        )
        self.stdout.write(
            self.style.NOTICE("FILE HYGIENE CLEANUP")
        )
        self.stdout.write(
            self.style.NOTICE(f"{'=' * 60}\n")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No files will be moved\n")
            )

        self.stdout.write(f"Scanning directory: {directory}")
        self.stdout.write(f"Recursive: {recursive}")
        self.stdout.write(f"Target: {FileHygiene.get_processed_dir()}\n")

        # Run cleanup
        results = FileHygiene.cleanup_loose_files(
            directory=directory,
            recursive=recursive,
            dry_run=dry_run,
        )

        if not results:
            self.stdout.write(
                self.style.SUCCESS("\n✓ No loose files found to clean up!")
            )
            return

        # Group results by extension
        by_extension = {}
        for result in results:
            ext = result["extension"]
            if ext not in by_extension:
                by_extension[ext] = []
            by_extension[ext].append(result)

        # Display results
        self.stdout.write(f"\nFound {len(results)} files:\n")
        
        for ext, files in sorted(by_extension.items()):
            self.stdout.write(f"\n{ext.upper()} files ({len(files)}):")
            for f in files[:10]:  # Show first 10 of each type
                size_kb = f["size_bytes"] / 1024
                action = f["action"]
                if action == "moved":
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {f['file']} ({size_kb:.1f} KB) -> {f.get('new_path', 'N/A')}")
                    )
                elif action == "would_move":
                    self.stdout.write(
                        self.style.WARNING(f"  → {f['file']} ({size_kb:.1f} KB)")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {f['file']} ({size_kb:.1f} KB) - FAILED")
                    )
            
            if len(files) > 10:
                self.stdout.write(f"  ... and {len(files) - 10} more")

        # Summary
        total_size = sum(r["size_bytes"] for r in results)
        moved = sum(1 for r in results if r["action"] == "moved")
        failed = sum(1 for r in results if r["action"] == "failed")

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"SUMMARY")
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"Total files: {len(results)}")
        self.stdout.write(f"Total size: {total_size / 1024 / 1024:.2f} MB")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"Would move: {len(results)} files")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Moved: {moved} files")
            )
            if failed:
                self.stdout.write(
                    self.style.ERROR(f"Failed: {failed} files")
                )

        self.stdout.write("")
