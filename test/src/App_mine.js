  const [showDataViewer, setShowDataViewer] = useState(false);
  const [performanceMode, setPerformanceMode] = useState(false);

  const toggleDataViewer = () => {
    setShowDataViewer(prev => !prev);
  };

  const togglePerformanceMode = () => {
    setPerformanceMode(prev => !prev);
  };
        <div className="app-controls">
          <button 
            className={`control-button ${showDataViewer ? 'active' : ''}`} 
            onClick={toggleDataViewer}
          >
            {showDataViewer ? 'Hide NWS Data Viewer' : 'Show NWS Data Viewer'}
          </button>
          <button 
            className={`control-button ${performanceMode ? 'active' : ''}`} 
            onClick={togglePerformanceMode}
          >
            {performanceMode ? 'Disable Performance Mode' : 'Enable Performance Mode'}
          </button>
        </div>
        <Filters />
        {showDataViewer && <NWSDataViewer />}
