/**
 * Enterprise Features Demo
 * 
 * This file demonstrates how to use the new enterprise features:
 * - Toast notifications
 * - Modal system with confirmations
 * - Error boundaries
 * - Skeleton loaders
 * - API client with retry logic
 * - React Query integration
 * 
 * @module ENTERPRISE_FEATURES_DEMO
 */

import { useState } from 'react';
import { useToast } from '@/contexts/ToastContext';
import { useModal } from '@/hooks/useModal';
import { Modal, ConfirmationModal } from '@/components/ui/Modal';
import { 
  Skeleton, 
  CardSkeleton, 
  TableSkeleton, 
  DashboardSkeleton 
} from '@/components/ui/Skeleton';
import { apiClient } from '@/core/api/client';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryKeys, queryClient } from '@/lib/query-client';

// =============================================================================
// 1. TOAST NOTIFICATIONS
// =============================================================================

export function ToastDemo() {
  const { success, error, warning, info } = useToast();

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-xl font-bold">Toast Notifications</h2>
      
      <button
        onClick={() => success('Operation completed successfully!')}
        className="px-4 py-2 bg-green-600 text-white rounded"
      >
        Show Success Toast
      </button>
      
      <button
        onClick={() => error('Something went wrong', { duration: 10000 })}
        className="px-4 py-2 bg-red-600 text-white rounded"
      >
        Show Error Toast (10s)
      </button>
      
      <button
        onClick={() => warning('This action cannot be undone', {
          action: { label: 'Undo', onClick: () => console.log('Undo clicked') }
        })}
        className="px-4 py-2 bg-yellow-600 text-white rounded"
      >
        Show Warning with Action
      </button>
      
      <button
        onClick={() => info('New updates available')}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        Show Info Toast
      </button>
    </div>
  );
}

// =============================================================================
// 2. MODAL SYSTEM
// =============================================================================

export function ModalDemo() {
  const basicModal = useModal();
  const confirmModal = useModal();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    await new Promise(resolve => setTimeout(resolve, 2000));
    setIsDeleting(false);
    confirmModal.close();
    console.log('Item deleted');
  };

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-xl font-bold">Modal System</h2>
      
      <button
        onClick={basicModal.open}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        Open Basic Modal
      </button>
      
      <button
        onClick={confirmModal.open}
        className="px-4 py-2 bg-red-600 text-white rounded"
      >
        Open Confirmation Modal
      </button>

      {/* Basic Modal */}
      <Modal
        isOpen={basicModal.isOpen}
        onClose={basicModal.close}
        title="User Profile"
        size="md"
        footer={
          <>
            <button
              onClick={basicModal.close}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded"
            >
              Cancel
            </button>
            <button
              onClick={basicModal.close}
              className="px-4 py-2 bg-blue-600 text-white rounded"
            >
              Save Changes
            </button>
          </>
        }
      >
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Name"
            className="w-full px-3 py-2 border rounded"
          />
          <input
            type="email"
            placeholder="Email"
            className="w-full px-3 py-2 border rounded"
          />
        </div>
      </Modal>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={confirmModal.close}
        onConfirm={handleDelete}
        title="Delete Item"
        message="Are you sure you want to delete this item? This action cannot be undone."
        confirmText="Delete"
        variant="danger"
        isLoading={isDeleting}
      />
    </div>
  );
}

// =============================================================================
// 3. SKELETON LOADERS
// =============================================================================

export function SkeletonDemo() {
  const [loading, setLoading] = useState(true);

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-xl font-bold">Skeleton Loaders</h2>
      
      <button
        onClick={() => setLoading(!loading)}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        Toggle Loading
      </button>

      {loading ? (
        <div className="space-y-6">
          <CardSkeleton />
          <TableSkeleton rows={5} />
          <DashboardSkeleton />
        </div>
      ) : (
        <div className="p-4 bg-white rounded shadow">
          <p>Content loaded successfully!</p>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 4. API CLIENT WITH RETRY LOGIC
// =============================================================================

export function APIClientDemo() {
  const { success, error } = useToast();

  const handleAPICall = async () => {
    try {
      // API client automatically retries on failure with exponential backoff
      const response = await apiClient.get('/api/stations/');
      success('Stations loaded successfully');
      console.log('Stations:', response.data);
    } catch (err) {
      error('Failed to load stations');
      console.error(err);
    }
  };

  const handleUpload = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiClient.upload('/api/reports/upload/', formData, {
        onUploadProgress: (progress) => {
          console.log(`Upload progress: ${progress}%`);
        },
      });
      
      success('File uploaded successfully');
      console.log('Upload response:', response.data);
    } catch (err) {
      error('Upload failed');
      console.error(err);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-xl font-bold">API Client</h2>
      
      <button
        onClick={handleAPICall}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        Fetch Stations (with auto-retry)
      </button>
      
      <input
        type="file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUpload(file);
        }}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />
    </div>
  );
}

// =============================================================================
// 5. REACT QUERY INTEGRATION
// =============================================================================

export function ReactQueryDemo() {
  const { success, error } = useToast();

  // Query with automatic caching, refetching, and error handling
  const { data: stations, isLoading, isError } = useQuery({
    queryKey: queryKeys.geojson.stations(),
    queryFn: async () => {
      const response = await apiClient.get('/api/stations/');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Mutation with optimistic updates
  const createStationMutation = useMutation({
    mutationFn: async (newStation: any) => {
      const response = await apiClient.post('/api/stations/', newStation);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch stations
      queryClient.invalidateQueries({ queryKey: queryKeys.geojson.stations() });
      success('Station created successfully');
    },
    onError: (err) => {
      error('Failed to create station');
      console.error(err);
    },
  });

  const handleCreateStation = () => {
    createStationMutation.mutate({
      name: 'New Station',
      latitude: 31.5204,
      longitude: 74.3587,
    });
  };

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-xl font-bold">React Query Integration</h2>
      
      {isLoading && <CardSkeleton />}
      
      {isError && (
        <div className="p-4 bg-red-50 text-red-700 rounded">
          Failed to load stations
        </div>
      )}
      
      {stations && (
        <div className="p-4 bg-white rounded shadow">
          <p>Loaded {stations.features?.length || 0} stations</p>
        </div>
      )}
      
      <button
        onClick={handleCreateStation}
        disabled={createStationMutation.isPending}
        className="px-4 py-2 bg-green-600 text-white rounded disabled:opacity-50"
      >
        {createStationMutation.isPending ? 'Creating...' : 'Create Station'}
      </button>
    </div>
  );
}

// =============================================================================
// FULL DEMO COMPONENT
// =============================================================================

export function EnterpriseDemo() {
  return (
    <div className="max-w-4xl mx-auto py-8 space-y-8">
      <h1 className="text-3xl font-bold text-center">Enterprise Features Demo</h1>
      
      <ToastDemo />
      <hr />
      
      <ModalDemo />
      <hr />
      
      <SkeletonDemo />
      <hr />
      
      <APIClientDemo />
      <hr />
      
      <ReactQueryDemo />
    </div>
  );
}

export default EnterpriseDemo;
