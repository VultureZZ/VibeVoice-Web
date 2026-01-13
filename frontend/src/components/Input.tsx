/**
 * Reusable input component.
 */

import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';

interface BaseInputProps {
  label?: string;
  error?: string;
}

interface TextInputProps
  extends InputHTMLAttributes<HTMLInputElement>,
    BaseInputProps {
  type?: 'text' | 'email' | 'password' | 'number' | 'url';
  textarea?: false;
}

interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement>,
    BaseInputProps {
  textarea: true;
}

type InputProps = TextInputProps | TextareaProps;

export const Input = forwardRef<
  HTMLInputElement | HTMLTextAreaElement,
  InputProps
>(({ label, error, className = '', ...props }, ref) => {
  const baseClasses =
    'w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500';
  const errorClasses = error
    ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
    : 'border-gray-300';

  const inputElement = props.textarea ? (
    <textarea
      ref={ref as React.Ref<HTMLTextAreaElement>}
      className={`${baseClasses} ${errorClasses} ${className}`}
      {...(props as TextareaProps)}
    />
  ) : (
    <input
      ref={ref as React.Ref<HTMLInputElement>}
      type={(props as TextInputProps).type || 'text'}
      className={`${baseClasses} ${errorClasses} ${className}`}
      {...(props as TextInputProps)}
    />
  );

  if (label) {
    return (
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
        {inputElement}
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
      {inputElement}
      {error && (
        <p className="mt-1 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </>
  );
});

Input.displayName = 'Input';
