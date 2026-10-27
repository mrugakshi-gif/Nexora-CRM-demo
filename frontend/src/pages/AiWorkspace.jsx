import React, { useState, useEffect, useRef, useCallback } from 'react';
import PageHeader from '../components/common/PageHeader';
import { aiAgentService, documentService } from '../services/crmService';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MessageSquare, BookOpen, Layers, Search, FileText, Trash2, Copy, ChevronDown, ChevronRight, FileDown, MoreVertical } from 'lucide-react';
import { auth as authService } from '../services/firebase';

const STATUS_REFRESH_INTERVAL = 3000;

function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 Bytes';
  const k = 1024, dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function StatusBadge({ status }) {
  const s = status.toLowerCase();
  let bg = '#f1f5f9', color = '#475569', text = status;
  if (s === 'completed') { bg = '#f0fdf4'; color = '#166534'; }
  else if (s === 'failed') { bg = '#fef2f2'; color = '#991b1b'; }
  else if (s.includes('uploading') || s.includes('extracting') || s.includes('chunking') || s.includes('embedding')) {
    bg = '#fff7ed'; color = '#9a3412'; 
  }
  return (
    <span style={{ background: bg, color: color, padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      {status !== 'Completed' && status !== 'Failed' && <div style={{ width: 6, height: 6, background: color, borderRadius: '50%', animation: 'pulse-dot 1s infinite' }} />}
      {text}
    </span>
  );
}

// ─── ASK CRM Tab ──────────────────────────────────────────────────────────────

let inFlightAiState = null;

function AskCrmTab() {
  const [messages, setMessages] = useState(inFlightAiState ? inFlightAiState.messages : []);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(inFlightAiState ? inFlightAiState.loading : false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(inFlightAiState ? inFlightAiState.activeSessionId : null);
  const [hoveredSessionId, setHoveredSessionId] = useState(null);
  const [menuOpenSessionId, setMenuOpenSessionId] = useState(null);
  const [isFocused, setIsFocused] = useState(false);
  const scrollRef = useRef(null);

  const fetchHistory = async () => {
    try {
      const res = await aiAgentService.getHistory();
      const sorted = (res.data || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setSessions(sorted);
    } catch (err) {
      console.error("Failed to fetch chat history", err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    let mounted = true;
    const currentInFlight = inFlightAiState;
    if (currentInFlight && currentInFlight.promise) {
      currentInFlight.promise.then(res => {
        if (!mounted) return;
        const assistantMsg = res.data;
        setMessages(prev => [...prev, { role: 'assistant', content: assistantMsg.content, id: assistantMsg.message_id || Date.now() }]);
        if (!currentInFlight.activeSessionId && assistantMsg.session_id) {
          setActiveSessionId(assistantMsg.session_id);
          fetchHistory();
        }
      }).catch(err => {
        if (!mounted) return;
        setMessages(prev => [...prev, { role: 'assistant', content: '❌ Sorry, I encountered an error communicating with the AI service. Please try again.', id: Date.now(), isError: true }]);
      }).finally(() => {
        if (!mounted) return;
        setLoading(false);
      });
    }
    return () => { mounted = false; };
  }, []);

  const scrollToBottom = () => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  };

  useEffect(() => { scrollToBottom(); }, [messages, loading]);

  const fileInputRef = useRef(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  const handleDeleteSession = async (sessionId) => {
    try {
      await aiAgentService.deleteSession(sessionId);
    } catch (e) {
      console.error("Failed to delete backend session or API missing:", e);
    }
    // Remove locally
    setSessions(prev => prev.filter(s => s.session_id !== sessionId));
    if (activeSessionId === sessionId) {
      startNewChat();
    }
  };

  const handleSend = async (text = input) => {
    if (!text.trim()) return;
    const userMsg = { role: 'user', content: text, id: Date.now() };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    const promise = aiAgentService.ask(text, activeSessionId);
    inFlightAiState = {
      messages: nextMessages,
      activeSessionId,
      loading: true,
      promise
    };

    try {
      const res = await promise;
      const assistantMsg = res.data;
      setMessages(prev => [...prev, { role: 'assistant', content: assistantMsg.content, id: assistantMsg.message_id || Date.now() }]);
      
      if (!activeSessionId && assistantMsg.session_id) {
        setActiveSessionId(assistantMsg.session_id);
        fetchHistory();
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Sorry, I encountered an error communicating with the AI service. Please try again.', id: Date.now(), isError: true }]);
    } finally {
      setLoading(false);
      inFlightAiState = null;
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const allowed = ['.pdf', '.docx', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      alert('Only PDF, DOCX, and TXT files are supported.');
      return;
    }
    
    setUploadingDoc(true);
    setUploadStatus(`Uploading ${file.name}...`);
    try {
      const formData = new FormData(); 
      formData.append('file', file);
      await documentService.uploadDocument(formData);
      setUploadStatus(`Processing ${file.name}...`);
      
      // Show immediate success message in chat. The backend processes chunks asynchronously.
      setMessages(prev => [...prev, { role: 'assistant', content: `✅ **${file.name}** is being processed in the background! It will appear in **Company Knowledge** and its chunks in **Chunk Explorer** shortly. You can ask questions about it once processing is complete.`, id: Date.now() }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ Failed to upload **${file.name}**: ${err.response?.data?.detail || err.message}`, id: Date.now(), isError: true }]);
    } finally {
      setUploadingDoc(false);
      setUploadStatus('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setInput('');
    setActiveSessionId(null);
    inFlightAiState = null;
  };

  const loadSession = (session) => {
    setActiveSessionId(session.session_id);
    setMessages(session.messages || []);
  };

  const suggestions = [
    'Show me my top 5 leads by score',
    'What is our enterprise pricing policy?',
    'Summarize recent won opportunities'
  ];

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-canvas)', overflow: 'hidden' }}>
      
      {/* Left Sidebar: Chat History */}
      <div style={{ width: 240, borderRight: '1px solid var(--border)', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', padding: '20px 16px', flexShrink: 0 }}>
        <button 
          onClick={startNewChat}
          style={{ width: '100%', padding: '10px 14px', background: 'var(--bg-subtle)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--accent-primary)', fontWeight: 700, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, transition: 'all 0.16s ease', marginBottom: 20, boxShadow: 'var(--clay-shadow-sm)' }}
          onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.background = 'var(--accent-tint)'; }}
          onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--bg-subtle)'; }}
        >
          <span style={{ fontSize: 16 }}>+</span> New Chat
        </button>

        <p style={{ margin: '0 0 12px', fontWeight: 800, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.8, color: 'var(--ink-mute)' }}>Recent</p>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto' }}>
          {sessions.map(s => {
            const isHovered = hoveredSessionId === s.session_id;
            const isMenuOpen = menuOpenSessionId === s.session_id;
            return (
              <div 
                key={s.session_id} 
                onMouseEnter={() => setHoveredSessionId(s.session_id)}
                onMouseLeave={() => setHoveredSessionId(null)}
                style={{ position: 'relative' }}
              >
                <button 
                  onClick={() => loadSession(s)}
                  style={{ 
                    width: '100%', textAlign: 'left', padding: '10px 12px', 
                    background: activeSessionId === s.session_id ? 'var(--accent-tint)' : (isHovered ? 'var(--bg-subtle)' : 'transparent'), 
                    border: '1px solid',
                    borderColor: activeSessionId === s.session_id ? 'var(--accent-primary)' : 'transparent',
                    borderRadius: 9, 
                    color: activeSessionId === s.session_id ? 'var(--heading-primary)' : 'var(--ink-soft)', 
                    fontSize: 13, fontWeight: activeSessionId === s.session_id ? 700 : 500, 
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                    transition: 'all 0.15s ease'
                  }}>
                  <MessageSquare size={14} color={activeSessionId === s.session_id ? 'var(--accent-primary)' : 'var(--ink-mute)'} /> 
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                    {s.messages && s.messages.length > 0 ? s.messages[0].content : 'Empty Chat'}
                  </span>
                  
                  {isHovered && (
                    <div 
                      onClick={(e) => { e.stopPropagation(); setMenuOpenSessionId(isMenuOpen ? null : s.session_id); }}
                      style={{ padding: 4, borderRadius: 4, background: isMenuOpen ? 'var(--bg-subtle)' : 'transparent', color: 'var(--ink-mute)', display: 'flex' }}>
                      <MoreVertical size={14} />
                    </div>
                  )}
                </button>
                
                {isMenuOpen && (
                  <div style={{ position: 'absolute', right: 0, top: 38, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--clay-shadow-float)', zIndex: 100, minWidth: 120, overflow: 'hidden' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <button 
                        onClick={(e) => { 
                          e.stopPropagation(); 
                          if (window.confirm('Are you sure you want to delete this chat?')) { 
                            handleDeleteSession(s.session_id); 
                          }
                          setMenuOpenSessionId(null); 
                        }} 
                        style={{ padding: '8px 16px', background: 'transparent', border: 'none', textAlign: 'left', fontSize: 13, cursor: 'pointer', color: 'var(--danger)' }} 
                        onMouseOver={e => e.currentTarget.style.background='var(--danger-bg)'} 
                        onMouseOut={e => e.currentTarget.style.background='transparent'}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          {sessions.length === 0 && (
             <div style={{ fontSize: 12, color: 'var(--ink-mute)', padding: '4px 0' }}>No recent chats</div>
          )}
        </div>
      </div>

      {/* Right Main Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        
        {messages.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
            <h1 style={{ margin: '0 0 8px', color: 'var(--heading-primary)', fontSize: 24, fontWeight: 800, letterSpacing: '-0.5px' }}>
              ASK YOUR CRM ANYTHING!
            </h1>
            <p style={{ margin: 0, color: 'var(--ink-mute)', fontSize: 13.5 }}>Instant AI answers across leads, deals, companies, and internal documents</p>
          </div>
        ) : (
          <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
            {messages.map(msg => (
              <div key={msg.id} style={{ display: 'flex', gap: 16, maxWidth: 850, margin: '0 auto', width: '100%', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', flexShrink: 0, background: msg.role === 'user' ? 'var(--accent-primary)' : 'var(--accent-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: msg.role === 'user' ? '#FFFFFF' : 'var(--accent-primary)', fontWeight: 700, fontSize: 15, boxShadow: 'var(--clay-shadow-sm)' }}>
                  {msg.role === 'user' ? 'U' : <MessageSquare size={18} />}
                </div>
                <div style={{ 
                  background: msg.role === 'user' ? 'var(--accent-primary)' : 'var(--bg-surface)', 
                  color: msg.role === 'user' ? '#FFFFFF' : 'var(--ink)',
                  padding: '16px 20px', borderRadius: 16, fontSize: 15, lineHeight: 1.6,
                  border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
                  boxShadow: msg.role === 'user' ? 'var(--clay-shadow-sm)' : 'var(--clay-shadow)',
                  maxWidth: '85%'
                }}>
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <div className="markdown-body" style={{ fontSize: 15 }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                  {msg.role === 'assistant' && !msg.isError && (
                    <button onClick={() => navigator.clipboard.writeText(msg.content)} style={{ background: 'transparent', border: 'none', color: 'var(--ink-mute)', cursor: 'pointer', padding: 0, marginTop: 12, display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, transition: 'color 0.15s ease' }} onMouseOver={e => e.currentTarget.style.color = 'var(--accent-primary)'} onMouseOut={e => e.currentTarget.style.color = 'var(--ink-mute)'}>
                      <Copy size={14} /> Copy Response
                    </button>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: 'flex', gap: 16, maxWidth: 850, margin: '0 auto', width: '100%' }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--accent-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--clay-shadow-sm)' }}>
                  <MessageSquare size={18} color="var(--accent-primary)" />
                </div>
                <div style={{ padding: '16px 20px', display: 'flex', gap: 6, alignItems: 'center', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 16, boxShadow: 'var(--clay-shadow-sm)' }}>
                  <div className="ai-dot" style={{ background: 'var(--accent-primary)', width: 8, height: 8 }}/>
                  <div className="ai-dot" style={{ animationDelay: '0.2s', background: 'var(--accent-primary)', width: 8, height: 8 }}/>
                  <div className="ai-dot" style={{ animationDelay: '0.4s', background: 'var(--accent-primary)', width: 8, height: 8 }}/>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Input Area */}
        <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          
          {/* Suggestions directly above input */}
          {messages.length === 0 && (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 800, marginBottom: 16 }}>
              {suggestions.map(q => (
                <button key={q} onClick={() => handleSend(q)}
                  style={{ padding: '8px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 20, fontSize: 13, color: 'var(--ink-soft)', cursor: 'pointer', transition: 'all 0.16s ease', boxShadow: 'var(--clay-shadow-sm)' }}
                  onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent-primary)'; e.currentTarget.style.color = 'var(--accent-primary)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
                  onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--ink-soft)'; e.currentTarget.style.transform = 'translateY(0)'; }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {uploadStatus && (
             <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', background: 'var(--accent-tint)', color: 'var(--accent-primary)', borderRadius: 20, fontSize: 13, fontWeight: 600, marginBottom: 12, border: '1px solid var(--border)' }}>
                <div style={{ width: 12, height: 12, border: '2px solid var(--accent-soft)', borderTop: '2px solid var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                {uploadStatus}
             </div>
          )}

          <div style={{ maxWidth: 800, width: '100%', position: 'relative' }}>
            <button 
              onClick={() => fileInputRef.current?.click()}
              style={{ position: 'absolute', left: 10, top: 10, width: 36, height: 36, borderRadius: 8, border: 'none', background: 'transparent', color: 'var(--ink-mute)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 300, transition: 'all 0.15s ease' }}
              onMouseOver={e => { e.currentTarget.style.background = 'var(--bg-subtle)'; e.currentTarget.style.color = 'var(--accent-primary)'; }}
              onMouseOut={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--ink-mute)'; }}
              title="Upload Document (PDF, DOCX, TXT)"
              disabled={uploadingDoc || loading}
            >
              +
            </button>
            <input type="file" ref={fileInputRef} onChange={handleUpload} accept=".pdf,.docx,.txt" style={{ display: 'none' }} />
            
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="ASK ANYTHING..."
              style={{ 
                width: '100%', 
                padding: '16px 50px 16px 50px', 
                borderRadius: 14, 
                border: '1px solid', 
                borderColor: isFocused ? 'var(--accent-primary)' : 'var(--border)', 
                background: 'var(--bg-surface)',
                color: 'var(--ink)',
                fontSize: 14.5, 
                resize: 'none', 
                minHeight: 56, 
                maxHeight: 150, 
                fontFamily: 'inherit', 
                boxShadow: isFocused ? '0 0 0 3px var(--accent-tint), var(--clay-recessed)' : 'var(--clay-recessed)',
                outline: 'none',
                transition: 'all 0.2s ease-in-out'
              }}
              rows={1}
              disabled={loading || uploadingDoc}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading || uploadingDoc}
              style={{ 
                position: 'absolute', right: 10, top: 10, width: 36, height: 36, borderRadius: 8, 
                background: input.trim() ? 'var(--accent-primary)' : 'var(--bg-subtle)', 
                color: input.trim() ? '#FFFFFF' : 'var(--ink-mute)', 
                border: 'none', cursor: input.trim() ? 'pointer' : 'default', 
                display: 'flex', alignItems: 'center', justifyContent: 'center', 
                transition: 'all 0.2s ease',
                boxShadow: input.trim() ? 'var(--clay-shadow-sm)' : 'none'
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Company Knowledge Tab ────────────────────────────────────────────────────

function CompanyKnowledgeTab({ onViewChunks }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  const fetchDocs = useCallback(async () => {
    try {
      const res = await documentService.listDocuments();
      setDocs(res.data || []);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
    pollingRef.current = setInterval(() => fetchDocs(), STATUS_REFRESH_INTERVAL);
    return () => clearInterval(pollingRef.current);
  }, [fetchDocs]);

  const handleUpload = async (file) => {
    if (!file) return;
    const allowed = ['.pdf', '.docx', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      setUploadError('Only PDF, DOCX, and TXT files are supported.');
      return;
    }
    setUploadError(''); setUploading(true);
    try {
      const formData = new FormData(); formData.append('file', file);
      await documentService.uploadDocument(formData);
      await fetchDocs();
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete ${filename} completely?`)) return;
    try {
      await documentService.deleteDocument(docId);
      await fetchDocs();
    } catch (err) { alert(err.response?.data?.detail || 'Delete failed.'); }
  };

  const handleViewDocument = async (docId) => {
    try {
        const token = await authService.currentUser?.getIdToken();
        const response = await fetch(`/api/documents/${docId}/view`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("Failed to load document");
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (err) {
        alert(err.message || 'Error viewing document');
    }
  };

  const inProgress = docs.some(d => ['Uploading','Extracting','Chunking','Generating Embeddings'].includes(d.processing_status));

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20, flex: 1, minHeight: 0, overflow: 'hidden' }}>
      <div onClick={() => !uploading && fileInputRef.current?.click()} onDragOver={e => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files?.[0]); }} style={{ border: `2px dashed ${dragOver ? 'var(--accent-primary)' : 'var(--border)'}`, borderRadius: 14, padding: '32px 24px', textAlign: 'center', background: dragOver ? 'var(--accent-tint)' : 'var(--bg-subtle)', cursor: uploading ? 'default' : 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, transition: 'all 0.18s ease' }}>
        <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt" style={{ display: 'none' }} onChange={e => handleUpload(e.target.files?.[0])} />
        {uploading ? (
          <><div style={{ width: 40, height: 40, border: '3px solid var(--border-soft)', borderTop: '3px solid var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} /><span style={{ color: 'var(--accent-primary)', fontWeight: 600, fontSize: 15 }}>Uploading…</span></>
        ) : (
          <><div style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--accent-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FileDown size={22} color="var(--accent-primary)" /></div><div><p style={{ margin: '0 0 4px', fontWeight: 800, color: 'var(--heading-primary)', fontSize: 15 }}>Drop a file here or click to upload</p><p style={{ margin: 0, color: 'var(--ink-mute)', fontSize: 13 }}>Supported: <strong>PDF</strong>, <strong>DOCX</strong>, <strong>TXT</strong></p></div></>
        )}
      </div>
      {uploadError && <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger)', borderRadius: 8, padding: '10px 14px', color: 'var(--danger-text)', fontSize: 13 }}>⚠️ {uploadError}</div>}
      
      {docs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--ink-mute)' }}><BookOpen size={40} style={{ marginBottom: 12, opacity: 0.5 }} /><p style={{ fontWeight: 700, color: 'var(--heading-primary)', marginBottom: 4 }}>No documents yet</p><p style={{ fontSize: 13 }}>Upload a PDF, DOCX, or TXT file to build your knowledge base.</p></div>
      ) : (
        <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflowY: 'auto', overflowX: 'hidden', background: 'var(--bg-surface)', flex: 1, minHeight: 0, boxShadow: 'var(--clay-shadow-sm)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}><tr style={{ background: 'var(--bg-subtle)' }}>{['Document', 'Type', 'Size', 'Chunks', 'Status', 'Actions'].map(h => <th key={h} style={{ position: 'sticky', top: 0, background: 'var(--bg-subtle)', padding: '11px 14px', textAlign: 'left', fontWeight: 700, color: 'var(--heading-primary)', whiteSpace: 'nowrap', borderBottom: '1px solid var(--border)', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>{h}</th>)}</tr></thead>
            <tbody>
              {docs.map((doc, i) => (
                <tr key={doc.doc_id} style={{ borderBottom: i < docs.length - 1 ? '1px solid var(--border-soft)' : 'none' }}>
                  <td style={{ padding: '12px 14px' }}><div style={{ fontWeight: 700, color: 'var(--heading-primary)' }}>{doc.title || doc.filename}</div><div style={{ color: 'var(--ink-mute)', fontSize: 11 }}>{doc.doc_id}</div></td>
                  <td style={{ padding: '12px 14px' }}><span style={{ background: 'var(--success-bg)', color: 'var(--success-text)', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>{doc.file_type || '—'}</span></td>
                  <td style={{ padding: '12px 14px', color: 'var(--ink-soft)' }}>{formatBytes(doc.file_size)}</td>
                  <td style={{ padding: '12px 14px', fontWeight: 700, color: 'var(--accent-primary)' }}>{doc.chunk_count ?? '—'}</td>
                  <td style={{ padding: '12px 14px' }}><StatusBadge status={doc.processing_status || 'Uploading'} /></td>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {doc.processing_status === 'Completed' && (
                        <>
                          <button onClick={() => handleViewDocument(doc.doc_id)} style={{ padding: '5px 10px', background: 'var(--bg-surface)', color: 'var(--accent-primary)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}><FileText size={14} /> View Document</button>
                          <button onClick={() => onViewChunks(doc)} style={{ padding: '5px 10px', background: 'var(--accent-tint)', color: 'var(--accent-primary)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}><Layers size={14} /> Explore Chunks</button>
                        </>
                      )}
                      <button onClick={() => handleDelete(doc.doc_id, doc.filename)} style={{ padding: '5px 10px', background: 'var(--danger-bg)', color: 'var(--danger-text)', border: '1px solid var(--danger-bg)', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}><Trash2 size={14} /> Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Chunk Explorer Tab ───────────────────────────────────────────────────────

function ChunkExplorerTab({ initialDoc }) {
  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(initialDoc || null);
  const [chunks, setChunks] = useState([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [search, setSearch] = useState('');
  const [expandedMeta, setExpandedMeta] = useState({});

  useEffect(() => {
    documentService.listDocuments().then(r => setDocs((r.data || []).filter(d => d.processing_status === 'Completed')));
  }, []);

  useEffect(() => { if (initialDoc) setSelectedDoc(initialDoc); }, [initialDoc]);

  useEffect(() => {
    if (!selectedDoc) { setChunks([]); return; }
    setLoadingChunks(true);
    documentService.getChunks(selectedDoc.doc_id).then(r => setChunks(r.data || [])).catch(() => setChunks([])).finally(() => setLoadingChunks(false));
  }, [selectedDoc]);

  const filtered = search.trim() ? chunks.filter(c => (c.text||'').toLowerCase().includes(search.toLowerCase()) || (c.original_text||'').toLowerCase().includes(search.toLowerCase())) : chunks;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{ width: 240, borderRight: '1px solid var(--border-soft)', overflowY: 'auto', padding: 16, background: 'var(--bg-subtle)', flexShrink: 0 }}>
        <p style={{ margin: '0 0 12px', fontWeight: 700, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.8, color: 'var(--ink-mute)' }}>Indexed Documents</p>
        {docs.map(doc => (
          <button key={doc.doc_id} onClick={() => setSelectedDoc(doc)} style={{ width: '100%', textAlign: 'left', padding: '10px 12px', borderRadius: 8, border: 'none', background: selectedDoc?.doc_id === doc.doc_id ? 'var(--accent-tint)' : 'transparent', color: selectedDoc?.doc_id === doc.doc_id ? 'var(--accent-primary)' : 'var(--ink)', fontWeight: selectedDoc?.doc_id === doc.doc_id ? 700 : 500, cursor: 'pointer', marginBottom: 4, fontSize: 13, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 200 }} title={doc.title || doc.filename}>{doc.title || doc.filename}</span>
            <span style={{ fontSize: 11, color: 'var(--ink-mute)', fontWeight: 400 }}>{doc.chunk_count} chunks</span>
          </button>
        ))}
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {!selectedDoc ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--ink-mute)', flexDirection: 'column', gap: 10 }}><Search size={36} /><p style={{ margin: 0, fontWeight: 600 }}>Select a document to explore its chunks</p></div>
        ) : (
          <>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-soft)', background: 'var(--bg-surface)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div><h4 style={{ margin: 0, fontWeight: 700, fontSize: 15, color: 'var(--heading-primary)' }}>{selectedDoc.title || selectedDoc.filename}</h4><p style={{ margin: 0, fontSize: 12, color: 'var(--ink-mute)', marginTop: 2 }}>{chunks.length} chunks</p></div>
              <div style={{ display: 'flex', alignItems: 'center', border: '1px solid var(--border-soft)', borderRadius: 20, padding: '0 12px', background: 'var(--bg-subtle)' }}><Search size={14} color="var(--ink-mute)" /><input type="text" style={{ border: 'none', padding: '8px 8px', outline: 'none', fontSize: 13, background: 'transparent', color: 'var(--ink)' }} placeholder="Search chunks…" value={search} onChange={e => setSearch(e.target.value)} /></div>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              {filtered.map((chunk, idx) => (
                <div key={chunk.chunk_id || idx} style={{ border: '1px solid var(--border-soft)', borderRadius: 10, background: 'var(--bg-surface)', padding: '16px', boxShadow: 'var(--clay-shadow-sm)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
                    <span style={{ background: 'var(--accent-tint)', color: 'var(--accent-primary)', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700 }}>Chunk #{(chunk.chunk_index ?? idx) + 1}</span>
                    {chunk.section && <span style={{ background: 'var(--bg-subtle)', color: 'var(--ink)', padding: '2px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600, border: '1px solid var(--border-soft)' }}>{chunk.section}</span>}
                    {chunk.subsection && <span style={{ background: 'var(--bg-subtle)', color: 'var(--ink-mute)', padding: '2px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600, border: '1px solid var(--border-soft)' }}>{chunk.subsection}</span>}
                    {chunk.page_number && <span style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#059669', padding: '2px 9px', borderRadius: 20, fontSize: 11, fontWeight: 600 }}>Page {chunk.page_number}</span>}
                    
                    <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                      <button onClick={() => setExpandedMeta(p => ({...p, [chunk.chunk_id || idx]: !p[chunk.chunk_id || idx]}))} style={{ padding: '4px 10px', background: 'transparent', color: 'var(--ink-mute)', border: '1px solid var(--border-soft)', borderRadius: 4, fontSize: 11, cursor: 'pointer', fontWeight: 600 }}>{expandedMeta[chunk.chunk_id || idx] ? 'Hide Metadata' : 'View Metadata'}</button>
                      <button onClick={() => navigator.clipboard.writeText(chunk.text)} style={{ padding: '4px 10px', background: 'var(--accent-tint)', color: 'var(--accent-primary)', border: '1px solid var(--border-soft)', borderRadius: 4, fontSize: 11, cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}><Copy size={12}/> Copy Contextualized</button>
                    </div>
                  </div>
                  
                  {expandedMeta[chunk.chunk_id || idx] && (
                    <div style={{ background: 'var(--bg-subtle)', padding: 12, borderRadius: 6, marginBottom: 12, fontSize: 12, fontFamily: 'monospace', color: 'var(--ink)', overflowX: 'auto', border: '1px solid var(--border-soft)' }}>
                      <strong>Document ID:</strong> {chunk.document_id || selectedDoc?.doc_id || 'N/A'} &nbsp;|&nbsp; <strong>Chunk ID:</strong> {chunk.chunk_id || 'N/A'}<br/>
                      <strong>Indexing Status:</strong> {chunk.indexing_status || 'Completed'} &nbsp;|&nbsp; <strong>Source Type:</strong> {chunk.source_file_type || selectedDoc?.file_type || 'N/A'}<br/>
                      <strong>Embedding Dimensions:</strong> 3072<br/>
                      <em style={{ color: 'var(--ink-mute)', fontSize: 11 }}>Note: Raw embeddings are withheld from API response.</em>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 20 }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: '0 0 6px', fontSize: 11, fontWeight: 700, color: 'var(--heading-primary)', textTransform: 'uppercase' }}>Contextualized RAG Chunk</p>
                      <div style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.6, background: 'var(--bg-subtle)', padding: '12px', borderRadius: 8, borderLeft: '3px solid var(--accent-primary)', whiteSpace: 'pre-wrap' }}>
                        {chunk.text}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const TABS = [
  { key: 'ask', label: 'ASK CRM', icon: <MessageSquare size={16} /> },
  { key: 'knowledge', label: 'Company Knowledge', icon: <BookOpen size={16} /> },
  { key: 'chunks', label: 'Chunk Explorer', icon: <Layers size={16} /> },
];

export default function AiWorkspace() {
  const [activeTab, setActiveTab] = useState('ask');
  const [chunkDoc, setChunkDoc] = useState(null);

  const handleViewChunks = (doc) => {
    setChunkDoc(doc);
    setActiveTab('chunks');
  };

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader title="AI Workspace" desc="Intelligent CRM assistant · Company knowledge base · RAG-powered document search" />
      <div style={{ padding: '0 28px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', paddingBottom: 28 }}>
        {/* Segmented Control Navigation Group */}
        <div style={{ marginBottom: '14px', display: 'flex', alignItems: 'center' }}>
          <div className="seg-tabbar" style={{
            display: 'inline-flex',
            gap: '6px',
            background: 'var(--bg-subtle)',
            padding: '5px',
            borderRadius: '14px',
            border: '1px solid var(--border-soft)',
            boxShadow: 'var(--clay-recessed)'
          }}>
            {TABS.map(tab => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  style={{
                    padding: '8px 18px',
                    border: 'none',
                    borderRadius: '10px',
                    background: isActive ? 'var(--bg-surface)' : 'transparent',
                    color: isActive ? 'var(--heading-primary)' : 'var(--ink-mute)',
                    fontWeight: isActive ? 700 : 500,
                    cursor: 'pointer',
                    fontSize: '13px',
                    transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: isActive ? 'var(--clay-shadow-sm), var(--clay-inset)' : 'none',
                    outline: 'none'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.color = 'var(--ink)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.color = 'var(--ink-mute)';
                  }}
                >
                  <span style={{ display: 'flex', color: isActive ? 'var(--accent-primary)' : 'var(--ink-mute)' }}>
                    {tab.icon}
                  </span>
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Container */}
        <div style={{ flex: 1, overflow: 'hidden', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '16px', boxShadow: 'var(--clay-shadow), var(--clay-inset)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: activeTab === 'ask' ? 'flex' : 'none', flex: 1, flexDirection: 'column', overflow: 'hidden' }}>
            <AskCrmTab />
          </div>
          <div style={{ display: activeTab === 'knowledge' ? 'flex' : 'none', flex: 1, flexDirection: 'column', overflow: 'hidden' }}>
            <CompanyKnowledgeTab onViewChunks={handleViewChunks} />
          </div>
          <div style={{ display: activeTab === 'chunks' ? 'flex' : 'none', flex: 1, flexDirection: 'column', overflow: 'hidden' }}>
            <ChunkExplorerTab initialDoc={chunkDoc} />
          </div>
        </div>
      </div>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.8); } }
        .ai-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; animation: ai-bounce 1.2s ease-in-out infinite; }
        @keyframes ai-bounce { 0%, 80%, 100% { transform: translateY(0); opacity: 0.5; } 40% { transform: translateY(-5px); opacity: 1; } }
        .markdown-body p { margin-top: 0; margin-bottom: 0.8em; }
        .markdown-body h1, .markdown-body h2, .markdown-body h3 { margin-top: 1em; margin-bottom: 0.5em; font-weight: 600; line-height: 1.25; color: var(--heading-primary); }
        .markdown-body ul, .markdown-body ol { margin-top: 0; margin-bottom: 0.8em; padding-left: 2em; }
        .markdown-body table { border-collapse: collapse; width: 100%; margin-bottom: 0.8em; }
        .markdown-body th, .markdown-body td { padding: 6px 13px; border: 1px solid var(--border-soft); }
        .markdown-body th { font-weight: 600; background: var(--bg-subtle); color: var(--heading-primary); }
        .markdown-body code { padding: 0.2em 0.4em; margin: 0; font-size: 85%; background-color: var(--bg-subtle); border-radius: 3px; font-family: monospace; }
        .markdown-body pre { padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; background-color: var(--bg-subtle); border-radius: 6px; }
        .markdown-body pre code { background: transparent; padding: 0; }
      `}</style>
    </div>
  );
}
