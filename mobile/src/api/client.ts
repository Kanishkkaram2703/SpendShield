import { API_BASE_URL, API_TIMEOUT_MS } from '../constants/config';

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  detail?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(message: string, status: number, code = 'api_error', details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  token?: string;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  const { body: requestBody, token, ...requestInit } = options;
  const headers = new Headers(requestInit.headers);
  headers.set('Accept', 'application/json');

  let body: BodyInit | undefined;
  if (requestBody !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(requestBody);
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestInit,
      body,
      headers,
      signal: controller.signal,
    });
    const text = await response.text();
    let payload: unknown;
    try {
      payload = text ? JSON.parse(text) : undefined;
    } catch {
      payload = undefined;
    }

    if (!response.ok) {
      const errorBody = payload as ApiErrorBody | undefined;
      const message = errorBody?.error?.message || errorBody?.detail;
      throw new ApiError(
        message || safeStatusMessage(response.status),
        response.status,
        errorBody?.error?.code || 'api_error',
        errorBody?.error?.details,
      );
    }

    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('The server took too long to respond.', 408, 'request_timeout');
    }
    throw new ApiError(
      'The backend could not be reached. Check the API URL and local network connection.',
      0,
      'network_error',
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

function safeStatusMessage(status: number): string {
  switch (status) {
    case 400:
      return 'The backend rejected this request. Check the development host configuration.';
    case 401:
      return 'Your session is not authorized. Please sign in again.';
    case 403:
      return 'The backend denied access to this request.';
    case 404:
      return 'The requested backend endpoint was not found. Check the API base path.';
    case 409:
      return 'This request conflicts with an existing account or operation.';
    case 422:
      return 'Please check the submitted fields and try again.';
    case 503:
      return 'The backend is temporarily unavailable. Please try again shortly.';
    case 500:
      return 'The backend encountered an internal error. Please try again shortly.';
    default:
      return 'The request could not be completed. Please try again.';
  }
}
