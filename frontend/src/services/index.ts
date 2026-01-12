/**
 * Services Barrel Export
 * 
 * @module services
 */

export { default as api, apiClient, get, post, put, patch, del } from './api';

// Exposure API (PM2.5, AQI, population at risk data)
export {
  exposureClient,
  get as exposureGet,
  post as exposurePost,
} from './exposureApi';
import * as exposureApi from './exposureApi';
export { exposureApi };
