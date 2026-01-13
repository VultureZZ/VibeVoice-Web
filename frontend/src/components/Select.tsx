/**
 * Reusable select/dropdown component.
 */

import { SelectHTMLAttributes, forwardRef } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className = '', ...props }, ref) => {
    const baseClasses =
      'w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white';
    const errorClasses = error
      ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
      : 'border-gray-300';

    const selectElement = (
      <select
        ref={ref}
        className={`${baseClasses} ${errorClasses} ${className}`}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );

    if (label) {
      return (
        <div className="w-full">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
          {selectElement}
          {error && (
            <p className="mt-1 text-sm text-red-600" role="alert">
              {error}
            </p>
          )}
        </div>
      );
    }

    return (
      <>
        {selectElement}
        {error && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
      </>
    );
  }
);

Select.displayName = 'Select';
