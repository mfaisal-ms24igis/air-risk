/**
 * AQI Risk Layer - Modular MapLibre Component
 * =============================================
 * 
 * A self-contained, reusable class for adding dynamic air quality
 * risk layers to MapLibre GL JS maps.
 * 
 * Features:
 * - Automatic tile fetching from Django API
 * - Dynamic legend generation
 * - Auto-refresh based on data freshness
 * - Event-driven architecture
 * - Full TypeScript support
 * 
 * Usage:
 * ```javascript
 * import { AqiRiskLayer } from '@/features/map/logic/AqiRiskLayer';
 * 
 * const riskLayer = new AqiRiskLayer(map, {
 *   apiBaseUrl: 'http://localhost:8000/api/v1/aqi-monitor',
 *   authToken: 'your-jwt-token',
 *   autoRefresh: true,
 *   refreshInterval: 300000 // 5 minutes
 * });
 * 
 * riskLayer.load();
 * ```
 * 
 * @author Principal Software Architect
 * @date December 11, 2025
 */

export interface RiskLayerOptions {
  apiBaseUrl: string;
  authToken?: string;
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
  hoursBack?: number;
  lookbackDays?: number;
  onLoad?: (data: RiskMapData) => void;
  onError?: (error: Error) => void;
  onRefresh?: (data: RiskMapData) => void;
}

export interface RiskMapData {
  tile_url: string;
  legend: LegendConfig;
  metadata: {
    sentinel_date: string;
    population_year: number;
    ground_stations: number;
    fusion_weights: {
      ground: number;
      satellite: number;
    };
    generated_at: string;
  };
}

export interface LegendConfig {
  title: string;
  type: string;
  stops: LegendStop[];
  unit: string;
}

export interface LegendStop {
  value: number;
  color: string;
  label: string;
}

export class AqiRiskLayer {
  private map: maplibregl.Map;
  private options: Required<RiskLayerOptions>;
  private refreshTimer: number | null = null;
  private legendElement: HTMLElement | null = null;
  private currentData: RiskMapData | null = null;
  private isLoading: boolean = false;

  // Layer IDs
  private readonly SOURCE_ID = 'aqi-risk-source';
  private readonly LAYER_ID = 'aqi-risk-layer';

  /**
   * Create a new AQI Risk Layer instance.
   * 
   * @param map MapLibre GL JS map instance
   * @param options Configuration options
   */
  constructor(map: maplibregl.Map, options: RiskLayerOptions) {
    this.map = map;

    // Set defaults
    this.options = {
      apiBaseUrl: options.apiBaseUrl,
      authToken: options.authToken || '',
      autoRefresh: options.autoRefresh ?? true,
      refreshInterval: options.refreshInterval || 300000, // 5 minutes
      hoursBack: options.hoursBack || 24,
      lookbackDays: options.lookbackDays || 30,
      onLoad: options.onLoad || (() => { }),
      onError: options.onError || ((error) => console.error('AqiRiskLayer error:', error)),
      onRefresh: options.onRefresh || (() => { })
    };
  }

  /**
   * Load the risk layer and add it to the map.
   */
  async load(): Promise<void> {
    if (this.isLoading) {
      console.warn('AqiRiskLayer: Load already in progress');
      return;
    }

    this.isLoading = true;

    try {
      // Fetch risk map data
      const data = await this.fetchRiskMapData();
      this.currentData = data;

      // Add raster source
      this.addRasterSource(data.tile_url);

      // Add raster layer
      this.addRasterLayer();

      // Generate legend
      this.createLegend(data.legend);

      // Setup auto-refresh if enabled
      if (this.options.autoRefresh) {
        this.startAutoRefresh();
      }

      // Fire onLoad callback
      this.options.onLoad(data);

      console.log('AqiRiskLayer: Loaded successfully', data.metadata);
    } catch (error) {
      this.options.onError(error as Error);
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Refresh the layer with new data.
   */
  async refresh(): Promise<void> {
    try {
      const data = await this.fetchRiskMapData();
      this.currentData = data;

      // Update source
      const source = this.map.getSource(this.SOURCE_ID) as maplibregl.RasterTileSource;
      if (source) {
        source.setTiles([data.tile_url]);
      }

      // Update legend
      this.updateLegend(data.legend);

      // Fire onRefresh callback
      this.options.onRefresh(data);

      console.log('AqiRiskLayer: Refreshed', data.metadata);
    } catch (error) {
      this.options.onError(error as Error);
    }
  }

  /**
   * Remove the layer from the map and cleanup resources.
   */
  destroy(): void {
    // Stop auto-refresh
    this.stopAutoRefresh();

    // Remove layer
    if (this.map.getLayer(this.LAYER_ID)) {
      this.map.removeLayer(this.LAYER_ID);
    }

    // Remove source
    if (this.map.getSource(this.SOURCE_ID)) {
      this.map.removeSource(this.SOURCE_ID);
    }

    // Remove legend
    if (this.legendElement && this.legendElement.parentNode) {
      this.legendElement.parentNode.removeChild(this.legendElement);
      this.legendElement = null;
    }

    console.log('AqiRiskLayer: Destroyed');
  }

  /**
   * Get current layer data.
   */
  getData(): RiskMapData | null {
    return this.currentData;
  }

  /**
   * Show/hide the layer.
   */
  setVisible(visible: boolean): void {
    const visibility = visible ? 'visible' : 'none';
    this.map.setLayoutProperty(this.LAYER_ID, 'visibility', visibility);
  }

  /**
   * Show/hide the legend.
   */
  setLegendVisible(visible: boolean): void {
    if (this.legendElement) {
      this.legendElement.style.display = visible ? 'block' : 'none';
    }
  }

  // ===== Private Methods =====

  /**
   * Fetch risk map data from Django API.
   */
  private async fetchRiskMapData(): Promise<RiskMapData> {
    const url = new URL(`${this.options.apiBaseUrl}/risk/tiles/`);
    url.searchParams.set('hours_back', this.options.hoursBack.toString());
    url.searchParams.set('lookback_days', this.options.lookbackDays.toString());

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    if (this.options.authToken) {
      headers['Authorization'] = `Bearer ${this.options.authToken}`;
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(`API Error: ${errorData.error || response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Add raster source to map.
   */
  private addRasterSource(tileUrl: string): void {
    if (this.map.getSource(this.SOURCE_ID)) {
      // Update existing source
      const source = this.map.getSource(this.SOURCE_ID) as maplibregl.RasterTileSource;
      source.setTiles([tileUrl]);
    } else {
      // Add new source
      this.map.addSource(this.SOURCE_ID, {
        type: 'raster',
        tiles: [tileUrl],
        tileSize: 256
      });
    }
  }

  /**
   * Add raster layer to map.
   */
  private addRasterLayer(): void {
    if (!this.map.getLayer(this.LAYER_ID)) {
      this.map.addLayer({
        id: this.LAYER_ID,
        type: 'raster',
        source: this.SOURCE_ID,
        paint: {
          'raster-opacity': 0.7,
          'raster-fade-duration': 300
        }
      });
    }
  }

  /**
   * Create legend DOM element.
   */
  private createLegend(config: LegendConfig): void {
    // Remove existing legend
    if (this.legendElement) {
      this.legendElement.remove();
    }

    // Create legend container
    const legend = document.createElement('div');
    legend.className = 'aqi-risk-legend';
    legend.innerHTML = `
      <div class="legend-title">${config.title}</div>
      <div class="legend-scale">
        ${config.stops.map(stop => `
          <div class="legend-item">
            <span class="legend-color" style="background-color: ${stop.color}"></span>
            <span class="legend-label">${stop.label} (${stop.value}${config.unit})</span>
          </div>
        `).join('')}
      </div>
    `;

    // Add to map container
    this.map.getContainer().appendChild(legend);
    this.legendElement = legend;
  }

  /**
   * Update existing legend.
   */
  private updateLegend(config: LegendConfig): void {
    if (this.legendElement) {
      this.legendElement.querySelector('.legend-title')!.textContent = config.title;
      // Update items...
    } else {
      this.createLegend(config);
    }
  }

  /**
   * Start auto-refresh timer.
   */
  private startAutoRefresh(): void {
    this.stopAutoRefresh();
    this.refreshTimer = window.setInterval(
      () => this.refresh(),
      this.options.refreshInterval
    );
  }

  /**
   * Stop auto-refresh timer.
   */
  private stopAutoRefresh(): void {
    if (this.refreshTimer !== null) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
}

export default AqiRiskLayer;
