import React, { useState, } from 'react';
import { fetchForumThreads } from './api/forumApi';
import LoadingModal from './components/LoadingModal';
import ThreadList from './components/ThreadList';

const App: React.FC = () => {
  const [threadUrls, setThreadUrls] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [threatDetected, setThreatDetected] = useState(false);

  const loadThreads = async () => {
    setIsLoading(true);
    try {
      const urls = await fetchForumThreads();
      setThreadUrls(urls);
      setThreatDetected(urls.length > 0);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>СтопФеминизм.рф</h1>
        <button 
          onClick={loadThreads} 
          disabled={isLoading}
          className="load-button"
        >
          Загрузить треды с форума
        </button>
      </header>
      
      {isLoading && (
        <LoadingModal 
          text="Идёт поиск феминизма. Загрузка может занять несколько минут"
          threatDetected={threatDetected}
          onClose={() => setIsLoading(false)}
        />
      )}
      
      <ThreadList threadUrls={threadUrls} />
    </div>
  );
};

export default App