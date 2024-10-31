/* LogComponent.js */

import React, { useEffect, useState, useRef } from 'react';
import '../DarkMode.css'; // Make sure this path is correct
import grtLogo from '../grt_logo.png';
import MetricsDisplay from './MetricsDisplay'; // Adjust the import path as necessary
import RightComponent from './RightComponent.js'; // Adjust the import path as necessary

const LogComponent = () => {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef(null);
  const frameRef = useRef(null); // This ref should be attached to the element with the scrollbar
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false); // Initially false to be hidden on mobile
  const [showRight, setShowRight] = useState(false);



  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    // Initial theme check
    const savedTheme = localStorage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // Function to toggle between dark and light theme
  const toggleTheme = () => {
    const newTheme = isDarkTheme ? 'light' : 'dark';
    setIsDarkTheme(!isDarkTheme);
    localStorage.setItem('theme', newTheme);
    document.body.className = `${newTheme}-theme`;
  };
  // Function to toggle Metrics and automatically close RightComponent
  const toggleShowMetrics = () => {
    setShowMetrics(prevState => !prevState);
    if (showRight) {
      setShowRight(false);
    }
  };

  // Function to toggle RightComponent and automatically close Metrics
  const toggleShowRight = () => {
    setShowRight(prevState => !prevState);
    if (showMetrics) {
      setShowMetrics(false);
    }
  };

  useEffect(() => {
    const setViewportHeight = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    };

    window.addEventListener('resize', setViewportHeight);
    setViewportHeight(); // Set the initial viewport height

    return () => window.removeEventListener('resize', setViewportHeight);
  }, []);

  // Effect hook to handle scroll and show/hide the scroll button
  useEffect(() => {
    const handleScroll = () => {
      const isNotAtBottom = frameRef.current.scrollHeight - frameRef.current.scrollTop > frameRef.current.clientHeight;
      setShowScrollButton(isNotAtBottom);
    };

    const frameElement = frameRef.current;
    frameElement.addEventListener('scroll', handleScroll);

    // Check scroll position initially
    handleScroll();

    return () => {
      frameElement.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // Effect hook for theme toggling
  useEffect(() => {
    document.body.className = isDarkTheme ? 'dark-theme' : 'light-theme';
  }, [isDarkTheme]);

  // Effect hook for handling new logs
  useEffect(() => {
    const initializeEventSource = () => {
      const clientID = localStorage.getItem("clientID") || Date.now().toString();
      localStorage.setItem("clientID", clientID);

      const url = new URL('https://192.168.41.49/stream');
      url.searchParams.append('client_id', clientID);

      const eventSource = new EventSource(url.toString());
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => setIsConnected(true);

      eventSource.onmessage = (event) => {
        const newLogs = JSON.parse(event.data);

        // Update logs
        setLogs((prevLogs) => [...prevLogs, ...newLogs]);

        // Auto-scroll if the user is already at the bottom
        if (isUserAtBottom()) {
          setTimeout(() => {
            scrollToBottom();
          }, 0);
        }
      };

      eventSource.onerror = (error) => {
        console.error('EventSource failed:', error);
        eventSource.close();
        setIsConnected(false);
      };
    };

    // Call this function to attempt reconnection
    const reconnectEventSource = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      initializeEventSource();
    };

    // Add visibility change event listener
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        reconnectEventSource();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Add online event listener
    window.addEventListener('online', reconnectEventSource);

    // Initialize the event source when the component mounts
    initializeEventSource();

    // Cleanup function to remove event listeners and close the event source
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('online', reconnectEventSource);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []); // Empty dependency array means this effect runs once on mount and cleanup on unmount


  const isUserAtBottom = () => {
    if (!frameRef.current) return false;

    const { scrollHeight, clientHeight, scrollTop } = frameRef.current;
    return scrollTop + clientHeight >= scrollHeight;
  };

  // Function to scroll to the bottom with smooth animation
  const scrollToBottom = () => {
    const contentContainer = frameRef.current;
    const scrollHeight = contentContainer.scrollHeight;
    const clientHeight = contentContainer.clientHeight;
    const currentScrollTop = contentContainer.scrollTop;
    const distanceToBottom = scrollHeight - clientHeight - currentScrollTop;
    const duration = 1000; // Adjust the duration as needed (in milliseconds)

    const startTime = performance.now();

    const scroll = (currentTime) => {
      const elapsedTime = currentTime - startTime;
      const easeInOutQuad = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      const targetScrollTop = currentScrollTop + distanceToBottom * easeInOutQuad(elapsedTime / duration);

      contentContainer.scrollTop = targetScrollTop;

      if (elapsedTime < duration) {
        requestAnimationFrame(scroll);
      } else {
        // Hide the button after a short delay
        setTimeout(() => {
          setShowScrollButton(false);
        }, 0); // Adjust the delay as needed (in milliseconds)
      }
    };

    requestAnimationFrame(scroll);
  };





  // Function to render ticket details
  const renderTicketDetails = (ticket) => {
    // If Serial Numbers are not in the expected object format, just display them as text.
    const renderSerialNumbers = (serialNumbers) => {
      if (typeof serialNumbers === 'object' && !Array.isArray(serialNumbers)) {
        return (
          <>
            <strong>Serial Number(s):</strong> {/* Header added here */}
            {Object.entries(serialNumbers).map(([part, serials], index) => (
              <div key={index} className="serial-number">
                <strong>{part}:</strong> {serials.join(', ')}
              </div>
            ))}
          </>
        );
      }
      return (
        <>
          <strong>Serial Number(s):</strong> {/* Header added here */}
          <div className="serial-number">{serialNumbers}</div>
        </>
      );
    };

    const detailKeysToExclude = new Set(['Equipment Ticket', 'Timestamp', 'Action', 'Action By']); // Define keys to exclude

    return (
      <>
        <div className="ticket-header">
          Equipment ticket {ticket['Equipment Ticket']} {ticket.Action} by {ticket['Action By']} - [{ticket.Timestamp}]
        </div>
        <div className="ticket-details">
          {Object.entries(ticket).map(([key, value], index) => {
            if (!detailKeysToExclude.has(key)) {
              if (key !== 'Serial Number(s)') {
                return (
                  <div key={index}>
                    <strong>{key}:</strong> {value}
                  </div>
                );
              }
              return renderSerialNumbers(value);
            }
            return null; // Exclude the header details from repeating below
          })}
        </div>
      </>
    );
  };

  return (
    <>
      <div className="header">
        <div className="logo-container">
          <img src={grtLogo} alt="GRT Logo" className="company-logo" />
        </div>
        <h1>Live Equipment Ticket Updates</h1>
        <div className="toggle-container">
          <div className="toggle-switch">
            <input type="checkbox" id="checkbox" checked={isDarkTheme} onChange={toggleTheme} />
            <label htmlFor="checkbox" className="slider"></label>
            <div className="toggle-label">Dark Mode</div>
          </div>
        </div>
      </div>
      <div className="app-container">
        <MetricsDisplay showMetrics={showMetrics} setShowMetrics={toggleShowMetrics} />
        <div className="content-container" ref={frameRef}>
          <div className="frame">
            {!isConnected && <div className="loading-message">Establishing connection...</div>}
            {isConnected && logs.length === 0 && <div className="loading-message">Awaiting new messages...</div>}
            {logs.map((log, index) => (
              <div key={index} className="message">
                {renderTicketDetails(log)}
              </div>
            ))}
          </div>
          {showScrollButton && (
            <div className="scroll-to-bottom" onClick={scrollToBottom}>
              <div className="scroll-arrow"></div>
            </div>
          )}
        </div>
        <RightComponent showRight={showRight} setShowRight={toggleShowRight} />
      </div>
    </>
  );
};

export default LogComponent;
