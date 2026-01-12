import React from 'react';
import { useStation, useStationReadings } from '@/hooks/queries';
import { StationProperties } from '@/types/models';

interface StationDetailPanelProps {
    station: StationProperties;
    onClose: () => void;
}

export function StationDetailPanel({ station: initialStation, onClose }: StationDetailPanelProps) {
    // Fetch full station details
    const { data: fullStation } = useStation(initialStation.id);

    // Fetch readings on demand
    const { data: readings, isLoading: isLoadingReadings, error: errorReadings } = useStationReadings(initialStation.id);

    // Use full details if available, otherwise fall back to initial props
    const displayStation = fullStation || initialStation;

    return (
        <div style={panelStyle}>
            <div style={headerStyle}>
                <div>
                    <h3 style={{ margin: 0, fontSize: '16px' }}>{displayStation.name}</h3>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                        {displayStation.city || 'Unknown City'}, {typeof displayStation.district === 'object' ? displayStation.district?.name : displayStation.district || 'Unknown District'}
                    </div>
                    <div style={{ fontSize: '11px', color: '#888', marginTop: '2px' }}>
                        Status: {displayStation.is_active ? 'Active' : 'Inactive'} •
                        Priority: {fullStation?.priority || 'N/A'}
                    </div>
                </div>
                <button onClick={onClose} style={closeButtonStyle}>×</button>
            </div>

            <div style={contentStyle}>
                {isLoadingReadings && <div style={{ padding: '20px', textAlign: 'center' }}>Loading data...</div>}

                {errorReadings && (
                    <div style={{ padding: '10px', color: 'red', fontSize: '12px' }}>
                        Failed to load readings.
                    </div>
                )}

                {/* Latest Readings Table */}
                {readings && readings.length > 0 && (
                    <div style={{ marginBottom: '20px' }}>
                        <h4 style={{ fontSize: '13px', margin: '10px 0' }}>Latest Readings</h4>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid #eee', textAlign: 'left' }}>
                                    <th style={{ padding: '8px 4px' }}>Param</th>
                                    <th style={{ padding: '8px 4px' }}>Value</th>
                                    <th style={{ padding: '8px 4px' }}>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {readings.map((reading) => (
                                    <tr
                                        key={reading.id}
                                        style={{ borderBottom: '1px solid #f5f5f5', cursor: 'pointer', backgroundColor: selectedPollutant === reading.parameter ? '#f0f9ff' : 'transparent' }}
                                        onClick={() => setSelectedPollutant(reading.parameter)}
                                    >
                                        <td style={{ padding: '8px 4px', fontWeight: 500 }}>{reading.parameter}</td>
                                        <td style={{ padding: '8px 4px' }}>
                                            {reading.value} <span style={{ color: '#888', fontSize: '11px' }}>{reading.unit}</span>
                                        </td>
                                        <td style={{ padding: '8px 4px', color: '#666', fontSize: '11px' }}>
                                            {new Date(reading.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        <div style={{ marginTop: '5px', fontSize: '10px', color: '#888', textAlign: 'center' }}>
                            Click a row to view chart
                        </div>
                    </div>
                )}

                {!isLoadingReadings && !readings?.length && (
                    <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                        No recent readings available.
                    </div>
                )}
            </div>
        </div>
    );
}

const panelStyle: React.CSSProperties = {
    position: 'absolute',
    top: '10px',
    right: '10px',
    width: '340px', // Slightly wider for chart
    maxHeight: 'calc(100% - 20px)',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    zIndex: 2000,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
};

const headerStyle: React.CSSProperties = {
    padding: '16px',
    borderBottom: '1px solid #eee',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    backgroundColor: '#f8f9fa',
};

const contentStyle: React.CSSProperties = {
    padding: '0 16px 16px 16px',
    overflowY: 'auto',
    flex: 1,
};

const closeButtonStyle: React.CSSProperties = {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    lineHeight: 1,
    cursor: 'pointer',
    color: '#666',
    padding: '0 4px',
};
