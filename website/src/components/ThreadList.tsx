import React, { useState, useEffect } from 'react';
import { fetchThreadContent, analyzeText, sendForumPost } from '../api/forumApi';

interface ThreadData {
  url: string;
  title?: string;
  content?: string;
  date?: string;
  isNegative?: boolean;
  gptResponse?: string;
  isLoading?: boolean;
  isAnalyzing?: boolean;
  isSending?: boolean;
  isSent?: boolean;
}

const ThreadList: React.FC<{ threadUrls: string[] }> = ({ threadUrls }) => {
  const [threads, setThreads] = useState<ThreadData[]>([]);
  const [showOnlyNegative, setShowOnlyNegative] = useState(false);
  const [processedUrls, setProcessedUrls] = useState<Set<string>>(new Set());
  const [cancelParsing, setCancelParsing] = useState(false);

  // Обработка тредов
  useEffect(() => {
    const processThreads = async () => {
      const threadsToProcess = threadUrls
        .filter(url => !processedUrls.has(url));

      if (threadsToProcess.length === 0 || cancelParsing) {
        setCancelParsing(false);
        return;
      }


      const newProcessedUrls = new Set(processedUrls);
      const newThreads = [...threads];

      // Добавляем заглушки для новых тредов
      threadsToProcess.forEach(url => {
        if (!newThreads.some(thread => thread.url === url)) {
          newThreads.push({ url, isLoading: true });
        }
      });

      setThreads([...newThreads]);

      for (const url of threadsToProcess) {
        if (cancelParsing) {
          setCancelParsing(false);
          break;
        }

        try {
          newProcessedUrls.add(url);

          const content = await fetchThreadContent(url);
          const analysis = await analyzeText(content.content || '');

          const threadData = {
            url,
            ...content,
            isNegative: analysis.negativity_detected,
            gptResponse: analysis.constructive_response,
            isLoading: false
          };

          // Сохраняем в БД все треды
          await sendToDatabase(threadData);

          newThreads[newThreads.findIndex(t => t.url === url)] = threadData;
          setThreads([...newThreads]);
        } catch (error) {
          console.error(`Error processing thread ${url}:`, error);
          newThreads.splice(newThreads.findIndex(t => t.url === url), 1);
        }
      }

      setProcessedUrls(new Set(newProcessedUrls));
    };

    processThreads();
  }, [threadUrls, cancelParsing]);

  // Фильтрация тредов
  const filteredThreads = showOnlyNegative
    ? threads.filter(t => t.isNegative)
    : threads;

  // Отправка в БД
  const sendToDatabase = async (thread: ThreadData) => {
    try {
      await fetch('http://localhost:5000/api/save_thread', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_url: thread.url,
          title: thread.title,
          content: thread.content,
          is_negative: thread.isNegative,
          date: thread.date,
          answer: thread.gptResponse || '',
          is_answer_sent: thread.isSent || false
        })
      });
    } catch (error) {
      console.error('Error saving to DB:', error);
    }
  };

  // Отправка ответа
  const handleSendResponse = async (url: string, response: string) => {
    try {
      setThreads(prev => prev.map(t =>
        t.url === url ? { ...t, isSending: true } : t
      ));

      const success = await sendForumPost(url, response);

      if (success) {
        setThreads(prev => prev.map(t =>
          t.url === url ? { ...t, isSending: false, isSent: true } : t
        ));

        await fetch('http://localhost:5000/api/update_thread', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_url: url,
            is_answer_sent: true
          })
        });
      }
    } catch (error) {
      console.error('Error sending response:', error);
      setThreads(prev => prev.map(t =>
        t.url === url ? { ...t, isSending: false } : t
      ));
    }
  };

  return (
    <div className="threads-container">
      <div className="thread-controls">
        <button
          className={`filter-button ${showOnlyNegative ? 'active' : ''}`}
          onClick={() => setShowOnlyNegative(!showOnlyNegative)}
        >
          {showOnlyNegative ? 'Показать все треды' : 'Показать только негативные'}
        </button>

      </div>

      <div className="threads-grid">
        {filteredThreads.map(thread => (
          <div key={thread.url} className={`thread-card ${thread.isNegative ? 'negative' : ''}`}>
            {thread.isLoading ? (
              <div className="thread-placeholder">
                <p>Идёт поиск угроз традиционным ценностям...</p>
              </div>
            ) : (
              <>
                <div className="thread-header">
                  <h3>
                    <a href={thread.url} target="_blank" rel="noopener noreferrer">
                      {thread.title || 'Без названия'}
                    </a>
                  </h3>
                  {thread.date && (
                    <span className="thread-date">
                      {new Date(thread.date).toLocaleString()}
                    </span>
                  )}
                </div>

                <div className="thread-content">
                  <p>{thread.content || 'Не удалось загрузить содержание'}</p>
                </div>

                {thread.isNegative && thread.gptResponse && (
                  <div className="thread-response">
                    <div className="gpt-response">
                      <h4>Ответ:</h4>
                      <p>{thread.gptResponse}</p>
                    </div>
                    <button
                      className="send-button"
                      onClick={() => handleSendResponse(thread.url, thread.gptResponse || '')}
                      disabled={thread.isSending || thread.isSent}
                    >
                      {thread.isSending ? 'Отправка...' :
                       thread.isSent ? '✓ Ответ отправлен' : 'Отправить ответ на форум'}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

    </div>
  );
};

export default ThreadList;
