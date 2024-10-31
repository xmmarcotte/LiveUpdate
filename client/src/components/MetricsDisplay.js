/* MetricsDisplay.js */
import React, { useEffect, useState } from 'react';

const MetricsDisplay = ({ showMetrics, setShowMetrics }) => {
    const [metrics, setMetrics] = useState(null);

    // Fetch the metrics from the backend
    const fetchMetrics = async () => {
        try {
            const response = await fetch('/api/smartsheet/metric-value', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    // Include other headers as required by your backend
                },
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setMetrics(data);
        } catch (error) {
            console.error('Failed to fetch metrics:', error);
        }
    };

    useEffect(() => {
        fetchMetrics();
        // Set an interval to refresh metrics every 20 minutes
        const intervalId = setInterval(fetchMetrics, 1200000);
        // Clear the interval on component unmount
        return () => clearInterval(intervalId);
    }, []);

    // Toggle the visibility of the metrics
    const toggleMetricsVisibility = () => {
        setShowMetrics(!showMetrics);
    };

    if (!metrics) {
        return (
            <div className={`metrics-container ${showMetrics ? 'show' : ''}`}>
                <button
                    className={`metrics-toggle-button ${showMetrics ? 'show' : ''}`}
                    onClick={toggleMetricsVisibility}
                >
                    {showMetrics ? '<' : '>'}
                </button>
                <div className="metrics-frame">
                    <div className='metrics-message'>Loading...</div>
                </div>
            </div>
        );
    }

    return (
        <div className={`metrics-container ${showMetrics ? 'show' : ''}`}>
            {/* This button will be used to toggle the visibility of metrics */}
            <button
                className="metrics-toggle-button"
                onClick={toggleMetricsVisibility}
            >
                {showMetrics ? '<' : '>'}
            </button>
            <div className="metrics-frame">
                {/* Map through the metrics and display them */}
                {Object.entries(metrics).map(([metricName, value], index) => (
                    <div key={index} className="metrics-message">
                        <div className="metrics-header">{metricName}</div>
                        {/* Make the whole div clickable */}
                        <a
                            href={getLinkForMetric(metricName)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="metrics-value"
                        >
                            {value}
                        </a>
                    </div>
                ))}
                {/* <div className='metrics-message'> */}
                <a
                    href='https://app.smartsheet.com/dashboards/3p89pmgG87m6jxMpGH3xf2xGRJCx2Gj9hFx4FG61'
                    target="_blank"
                    rel="noopener noreferrer"
                    className="metrics-header"
                    margin-left="20px"
                    margin-right="20px"
                >
                    View Dashboard
                </a>
                {/* </div> */}
            </div>
        </div>
    );
};

// Function to get the appropriate link for each metric
const getLinkForMetric = (metricName) => {
    switch (metricName) {
        case 'Average Days to Ship':
        case 'Tickets Shipped (Past 30 Days)':
        case 'Shipping Variance (Actual Ship vs Requested Ship)':
            return `https://app.smartsheet.com/reports/mX2cm43MhhcxJfr5j28ww88WqHhcc5x3hmw6jC61`;
        case 'Current Open Tickets':
        case 'Tickets Created (Past 30 Days)':
            return `https://app.smartsheet.com/sheets/4VQRqX9wFc2HQXpjcjm4RP8P24G3wjqjc5cXJHp1`;
        case 'Active Escalations':
            return `https://app.smartsheet.com/reports/PM4q45w5MM9Xfrj9xqhvCCxJmqMjR4gcgrwHvFQ1`;
        default:
            return '#'; // Default to "#" if no link is specified
    }
};

export default MetricsDisplay;
