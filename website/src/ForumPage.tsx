import React, { useState } from 'react';
import { fetchForumLinks, fetchTopicDetails, checkNegativityBatch, sendForumPost } from './api';
import { ForumPost } from './types';

const ForumPage: React.FC = () => {
  const [links, setLinks] = useState<string[]>([]);
  const [posts, setPosts] = useState<ForumPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batchSize] = useState(10);
  const [currentBatch, setCurrentBatch] = useState(0);

  const loadForumLinks = async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchedLinks = await fetchForumLinks();
      setLinks(fetchedLinks);
      setPosts([]);
      setCurrentBatch(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const loadPostsBatch = async () => {
    if (links.length === 0) return;
    
    setLoading(true);
    setError(null);
    try {
      const start = currentBatch * batchSize;
      const end = start + batchSize;
      const batchLinks = links.slice(start, end);
      
      const fetchedPosts = await fetchTopicDetails(batchLinks);
      setPosts(prev => [...prev, ...fetchedPosts]);
      setCurrentBatch(prev => prev + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const checkNegativity = async () => {
    if (posts.length === 0) return;
    
    setLoading(true);
    setError(null);
    try {
      const start = (currentBatch - 1) * batchSize;
      const end = start + batchSize;
      const batchPosts = posts.slice(start, end);
      
      const checkedPosts = await checkNegativityBatch(batchPosts);
      
      setPosts(prev => {
        const newPosts = [...prev];
        for (let i = 0; i < checkedPosts.length; i++) {
          newPosts[start + i] = checkedPosts[i];
        }
        return newPosts;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const regenerateResponse = async (postIndex: number) => {
    if (!posts[postIndex]?.comment) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await checkNegativityBatch([{
        link: posts[postIndex].link,
        title: posts[postIndex].title,
        comment: posts[postIndex].comment
      }]);
      
      if (response.length > 0) {
        setPosts(prev => {
          const newPosts = [...prev];
          newPosts[postIndex] = response[0];
          return newPosts;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate response');
    } finally {
      setLoading(false);
    }
  };

  const handleSendPost = async (url: string, message: string) => {
    setLoading(true);
    setError(null);
    try {
      const success = await sendForumPost(url, message);
      if (!success) {
        throw new Error('Failed to send post');
      }
      alert('Пост успешно отправлен!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send post');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="forum-page">
      <h1>СтопФеминизм.рф</h1>
      
      <div className="controls">
        <button onClick={loadForumLinks} disabled={loading}>
          {loading ? 'Загрузка...' : 'Загрузить посты форума'}
        </button>
        
        {links.length > 0 && (
          <button onClick={loadPostsBatch} disabled={loading || posts.length >= links.length}>
            {loading ? 'Загрузка...' : 
             currentBatch === 0 ? 'Загрузить первые 10 постов' : 'Загрузить следующие 10 постов'}
          </button>
        )}
        
        {posts.length > 0 && (
          <button onClick={checkNegativity} disabled={loading}>
            {loading ? 'Проверка...' : 'Проверить на негатив'}
          </button>
        )}
      </div>
      
      {error && <div className="error">{error}</div>}
      
      <div className="stats">
        {links.length > 0 && (
          <p>Загружено ссылок: {links.length} | Показано постов: {posts.length}</p>
        )}
      </div>
      
      <div className="posts-container">
        {links.length > 0 && posts.length === 0 && (
          <ul className="links-list">
            {links.slice(0, currentBatch * batchSize).map((link, index) => (
              <li key={index}>
                <a href={link} target="_blank" rel="noopener noreferrer">
                  {link}
                </a>
              </li>
            ))}
          </ul>
        )}
        
        {posts.length > 0 && (
          <div className="posts-grid">
            {posts.map((post, index) => (
              <div 
                key={index} 
                className={`post-card ${post.negativity_detected ? 'negative' : ''}`}
              >
                <h3>
                  <a href={post.link} target="_blank" rel="noopener noreferrer">
                    {post.title || 'Без заголовка'}
                  </a>
                </h3>
                
                {post.negativity_detected && (
                  <div className="negativity-label">НЕГАТИВ</div>
                )}
                
                <p className="comment">{post.comment}</p>
                
                {post.gpt_response && (
                  <div className="gpt-response">
                    <h4>Конструктивный ответ:</h4>
                    <p>{post.gpt_response}</p>
                    <div className="response-actions">
                      <button 
                        onClick={() => regenerateResponse(index)}
                        disabled={loading}
                        className="regenerate-btn"
                      >
                        Сгенерировать заново
                      </button>
                      <button 
                        onClick={() => handleSendPost(post.link, post.gpt_response!)}
                        disabled={loading}
                        className="send-btn"
                      >
                        Отправить на форум
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ForumPage;
