/**
 * useModal Hook
 * 
 * Convenience hook for managing modal state
 * 
 * @module hooks/useModal
 */

import { useState, useCallback } from 'react';

export interface UseModalReturn {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

/**
 * Hook to manage modal state
 * 
 * @example
 * ```tsx
 * const deleteModal = useModal();
 * 
 * <button onClick={deleteModal.open}>Delete</button>
 * <ConfirmationModal
 *   isOpen={deleteModal.isOpen}
 *   onClose={deleteModal.close}
 *   onConfirm={handleDelete}
 *   title="Delete Item"
 *   message="Are you sure?"
 * />
 * ```
 */
export function useModal(initialState = false): UseModalReturn {
  const [isOpen, setIsOpen] = useState(initialState);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}

export default useModal;
