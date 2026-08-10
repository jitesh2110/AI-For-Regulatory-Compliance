import React, { useState, useRef, useEffect } from 'react';
import { Shield, UploadCloud, File as FileIcon, Loader2, Database, BrainCircuit, CheckCircle2, FolderSearch, ChevronRight, Download, PlayCircle, AlertCircle, Search, FileDown, Users, Zap, Info, ArrowRight, Send, Mail, Trash2, Plus, Edit2, X, Check, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function App() {
  const [role, setRole] = useState('manager'); // 'manager' or 'employee'
  const [activeTab, setActiveTab] = useState('batch'); // 'batch', 'ondemand', 'recipients'

  // COMMUNICATION CENTER STATE
  const [recipients, setRecipients] = useState([]);
  const [newEmail, setNewEmail] = useState('');
  const [isDispatching, setIsDispatching] = useState(false);
  
  // EDIT RECIPIENT STATE
  const [editingEmail, setEditingEmail] = useState(null);
  const [editValue, setEditValue] = useState('');

  // CHATBOT STATE
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (activeTab === 'recipients') {
      fetchRecipients();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'chat' && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, activeTab, isTyping]);

  const fetchRecipients = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5000/api/recipients');
      if (res.ok) setRecipients(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const addRecipient = async (e) => {
    e.preventDefault();
    if (!newEmail) return;
    try {
      const res = await fetch('http://127.0.0.1:5000/api/recipients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: newEmail })
      });
      if (res.ok) {
        setNewEmail('');
        fetchRecipients();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteRecipient = async (email) => {
    if (!window.confirm(`Are you sure you want to remove ${email} from the distribution list?`)) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/recipients/${email}`, {
        method: 'DELETE'
      });
      if (res.ok) fetchRecipients();
    } catch (e) {
      console.error(e);
    }
  };

  const startEdit = (email) => {
    setEditingEmail(email);
    setEditValue(email);
  };

  const cancelEdit = () => {
    setEditingEmail(null);
    setEditValue('');
  };

  const saveEdit = async (oldEmail) => {
    if (!editValue || editValue === oldEmail) {
      cancelEdit();
      return;
    }
    try {
      const res = await fetch('http://127.0.0.1:5000/api/recipients', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_email: oldEmail, new_email: editValue })
      });
      if (res.ok) {
        fetchRecipients();
        cancelEdit();
      } else {
        const data = await res.json();
        alert(data.error || "Failed to update recipient");
      }
    } catch (e) {
      console.error(e);
      alert("Error updating recipient");
    }
  };

  const dispatchAudit = async (filename, content) => {
    try {
      setIsDispatching(true);
      const safeFilename = filename.replace(/[^a-zA-Z0-9.\-_]/g, '_');
      const response = await fetch('http://127.0.0.1:5000/api/dispatch_audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: safeFilename, content })
      });

      if (!response.ok) throw new Error("Dispatch failed on the server.");
      
      const data = await response.json();
      alert(data.message || "Audit dispatched successfully!");
    } catch (err) {
      console.error(err);
      alert(`Error dispatching audit: ${err.message}`);
    } finally {
      setIsDispatching(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setIsTyping(true);

    try {
      const res = await fetch('http://127.0.0.1:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: 'ai', text: data.response }]);
      } else {
        setChatMessages(prev => [...prev, { role: 'ai', text: "Sorry, I encountered an error. Please try again." }]);
      }
    } catch (e) {
      console.error(e);
      setChatMessages(prev => [...prev, { role: 'ai', text: "Connection error. Ensure the server is running." }]);
    } finally {
      setIsTyping(false);
    }
  };

  // EMPLOYEE PORTAL STATE
  const [employeeUpdates, setEmployeeUpdates] = useState([]);
  const [flashAlerts, setFlashAlerts] = useState([]);
  const [employeeLoading, setEmployeeLoading] = useState(false);

  useEffect(() => {
    if (role === 'employee') {
      fetchEmployeeData();
    }
  }, [role]);

  const fetchEmployeeData = async () => {
    setEmployeeLoading(true);
    try {
      const updatesRes = await fetch('http://127.0.0.1:5000/api/employee/updates');
      if (updatesRes.ok) setEmployeeUpdates(await updatesRes.json());

      const alertsRes = await fetch('http://127.0.0.1:5000/api/employee/flash_alerts');
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setFlashAlerts(data.alerts || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setEmployeeLoading(false);
    }
  };

  // ON-DEMAND AUDIT STATE
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, analyzing_db, streaming_ai, complete
  const [policies, setPolicies] = useState([]);
  const [streamText, setStreamText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const terminalEndRef = useRef(null);

  // BATCH AUDIT STATE
  const [batchStatus, setBatchStatus] = useState('idle'); // idle, scanning, ready
  const [queue, setQueue] = useState([]); // [{ id, filename, pdf_text, context, policies, status, memo }]
  const [selectedFileId, setSelectedFileId] = useState(null);

  // UPDATED: Changed from isGeneratingPdf to isGeneratingDocx
  const [isGeneratingDocx, setIsGeneratingDocx] = useState(false);

  // Auto-scroll terminal in on-demand mode
  useEffect(() => {
    if (activeTab === 'ondemand' && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamText, activeTab]);

  // UPDATED: downloadDocx function
  const downloadDocx = async (filename, content) => {
    try {
      setIsGeneratingDocx(true);
      const safeFilename = filename.replace(/[^a-zA-Z0-9.\-_]/g, '_');

      // UPDATED: Endpoint changed to /api/generate_docx
      const response = await fetch('http://127.0.0.1:5000/api/generate_docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: safeFilename, content })
      });

      if (!response.ok) throw new Error("DOCX Generation failed on the server.");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // UPDATED: File extension changed to .docx
      a.download = `${safeFilename.replace('.pdf', '')}_RegAI_Memo.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert(`Error downloading DOCX: ${err.message}`);
    } finally {
      setIsGeneratingDocx(false);
    }
  };

  // ON-DEMAND LOGIC
  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf' || droppedFile.name.endsWith('.pdf')) setFile(droppedFile);
      else alert("Please upload a valid PDF file.");
    }
  };
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) setFile(e.target.files[0]);
  };

  const runOnDemandAudit = async () => {
    if (!file) return;
    try {
      setStatus('analyzing_db'); setPolicies([]); setStreamText('');
      const formData = new FormData(); formData.append('file', file);

      const dbResponse = await fetch('http://127.0.0.1:5000/api/analyze_upload', { method: 'POST', body: formData });
      if (!dbResponse.ok) throw new Error(`DB Error: ${dbResponse.statusText}`);

      const dbData = await dbResponse.json();
      setPolicies(dbData.policies || []);

      setStatus('streaming_ai');
      const streamResponse = await fetch('http://127.0.0.1:5000/api/stream_audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pdf_text: dbData.pdf_text || '', policy_context: dbData.context || '' })
      });
      if (!streamResponse.ok) throw new Error(`Stream Error: ${streamResponse.statusText}`);

      const reader = streamResponse.body.getReader();
      const decoder = new TextDecoder('utf-8');
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setStreamText((prev) => prev + chunk);
      }
      setStatus('complete');
    } catch (error) {
      console.error(error); alert(`Error: ${error.message}`); setStatus('idle');
    }
  };

  // BATCH LOGIC
  const scanFolder = async () => {
    try {
      setBatchStatus('scanning');
      setQueue([]);
      setSelectedFileId(null);
      const response = await fetch('http://127.0.0.1:5000/api/analyze_folder');
      if (!response.ok) throw new Error(`Scan Error: ${response.statusText}`);

      const data = await response.json();
      if (!data.files || data.files.length === 0) {
        alert("No PDFs found in the downloaded_notices folder.");
        setBatchStatus('idle');
        return;
      }

      const initialQueue = data.files.map((item, index) => ({
        ...item,
        id: `file-${index}-${Date.now()}`,
        status: 'queued', // queued, processing, completed, failed
        memo: ''
      }));

      setQueue(initialQueue);
      setBatchStatus('ready');
      if (initialQueue.length > 0) {
        setSelectedFileId(initialQueue[0].id);
      }

    } catch (error) {
      console.error(error); alert(`Error: ${error.message}`); setBatchStatus('idle');
    }
  };

  const startAudit = async (id) => {
    const isAnyProcessing = queue.some(q => q.status === 'processing');
    if (isAnyProcessing) {
      alert("Another audit is currently processing. Please wait to prevent GPU overload.");
      return;
    }

    setQueue(prev => prev.map(q => q.id === id ? { ...q, status: 'processing', memo: '' } : q));

    const fileToProcess = queue.find(q => q.id === id);

    try {
      const streamResponse = await fetch('http://127.0.0.1:5000/api/stream_audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pdf_text: fileToProcess.pdf_text,
          policy_context: fileToProcess.context
        })
      });

      if (!streamResponse.ok) throw new Error("Stream failed");

      const reader = streamResponse.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });

        setQueue(prev => prev.map(q => {
          if (q.id === id) {
            return { ...q, memo: q.memo + chunk };
          }
          return q;
        }));
      }

      setQueue(prev => prev.map(q => q.id === id ? { ...q, status: 'completed' } : q));

    } catch (err) {
      console.error("Batch stream error", err);
      setQueue(prev => prev.map(q => q.id === id ? { ...q, status: 'failed', memo: q.memo + `\n\n[Error: ${err.message}]` } : q));
    }
  };

  const selectedFileItem = queue.find(q => q.id === selectedFileId);
  const isAnyProcessing = queue.some(q => q.status === 'processing');
  const completedCount = queue.filter(q => q.status === 'completed').length;
  const totalCount = queue.length;

  return (
    <div className="min-h-screen flex flex-col font-sans">
      {/* Header */}
      <header className="flex justify-between items-center p-4 px-8 cyber-panel sticky top-0 z-10 border-b border-cyber-border/50 bg-cyber-panel/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Shield className="text-cyber-accent" size={28} />
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyber-accent to-cyber-glow bg-clip-text text-transparent">
            RegAI
          </h1>
        </div>
        <div className="flex gap-6 items-center">
          {/* Role Switcher */}
          <div className="flex items-center gap-2 bg-black/40 p-1 rounded-full border border-cyber-border mr-4">
            <button
              onClick={() => setRole('manager')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-all ${role === 'manager' ? 'bg-cyber-accent text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Manager View
            </button>
            <button
              onClick={() => setRole('employee')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-all flex items-center gap-2 ${role === 'employee' ? 'bg-[#10b981] text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
            >
              <Users size={16} /> Employee Portal
            </button>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/50 px-4 py-1.5 rounded-full border border-cyber-border text-sm font-medium">
            <Database size={16} className="text-slate-400" />
            <span className="text-slate-200">DB: Online</span>
            <div className="w-2 h-2 rounded-full bg-cyber-success shadow-[0_0_8px_#10b981] animate-pulse"></div>
          </div>
          <div className="flex items-center gap-2 bg-slate-800/50 px-4 py-1.5 rounded-full border border-cyber-border text-sm font-medium">
            <BrainCircuit size={16} className="text-slate-400" />
            <span className="text-slate-200">AI: Ready</span>
            <div className="w-2 h-2 rounded-full bg-cyber-success shadow-[0_0_8px_#10b981] animate-pulse"></div>
          </div>
        </div>
      </header>

      {/* Tabs - Only for Manager */}
      {role === 'manager' ? (
        <>
          <div className="flex justify-center mt-8 px-4 mb-8">
            <div className="bg-cyber-panel p-1 rounded-xl border border-cyber-border inline-flex">
              <button
                className={`px-8 py-2.5 rounded-lg font-semibold text-sm transition-all duration-200 ${activeTab === 'batch' ? 'bg-cyber-accent text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                onClick={() => setActiveTab('batch')}
              >
                Batch Command
              </button>
              <button 
                className={`px-8 py-2.5 rounded-lg font-semibold text-sm transition-all duration-200 ${activeTab === 'ondemand' ? 'bg-cyber-accent text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                onClick={() => setActiveTab('ondemand')}
              >
                On-Demand Audit
              </button>
              <button 
                className={`px-8 py-2.5 rounded-lg font-semibold text-sm transition-all duration-200 ${activeTab === 'recipients' ? 'bg-cyber-accent text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                onClick={() => setActiveTab('recipients')}
              >
                Recipient Manager
              </button>
              <button 
                className={`px-8 py-2.5 rounded-lg font-semibold text-sm transition-all duration-200 ${activeTab === 'chat' ? 'bg-[#E03546] text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
                onClick={() => setActiveTab('chat')}
              >
                Ask RegAI
              </button>
            </div>
          </div>

          <main className="flex-1 w-full max-w-7xl mx-auto px-4 pb-8 flex flex-col">

            {/* --- TAB 1: BATCH COMMAND --- */}
            {activeTab === 'batch' && (
              <div className="flex flex-col flex-1 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex justify-between items-end mb-6">
                  <div>
                    <h2 className="text-3xl font-bold text-slate-100 mb-2">Bulk Regulatory Analysis</h2>
                    <p className="text-slate-400">Master-Detail Workspace: Select a notice from the queue to process or view its AI memo.</p>
                  </div>
                  <div>
                    <button
                      className="cyber-button flex items-center gap-2"
                      onClick={scanFolder}
                      disabled={batchStatus === 'scanning' || isAnyProcessing}
                    >
                      {batchStatus === 'scanning' ? <><Loader2 className="animate-spin" size={20} /> Scanning Folder...</> :
                        <><FolderSearch size={20} /> Scan Local Folder</>}
                    </button>
                  </div>
                </div>

                {queue.length > 0 && (
                  <div className="flex flex-1 gap-6 h-[700px]">

                    {/* Master: Sidebar Queue (30%) */}
                    <div className="w-[30%] cyber-panel rounded-xl flex flex-col overflow-hidden">
                      <div className="p-4 border-b border-cyber-border bg-white/5 flex justify-between items-center">
                        <h3 className="font-semibold text-slate-200 flex items-center gap-2">
                          <Database size={16} className="text-cyber-accent" /> Document Queue
                        </h3>
                        <span className="text-xs bg-slate-800 px-2 py-1 rounded-full text-slate-400 border border-slate-700">
                          {completedCount}/{totalCount} Done
                        </span>
                      </div>

                      <div className="flex-1 overflow-y-auto p-3 space-y-2">
                        {queue.map((item) => (
                          <div
                            key={item.id}
                            onClick={() => setSelectedFileId(item.id)}
                            className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 flex items-center justify-between group ${selectedFileId === item.id
                                ? 'bg-cyber-accent/10 border-cyber-accent shadow-[0_0_10px_rgba(59,130,246,0.15)]'
                                : 'bg-white/5 border-transparent hover:border-slate-600'
                              }`}
                          >
                            <div className="flex items-center gap-3 truncate pr-3">
                              {item.status === 'queued' && <FileIcon size={16} className="text-slate-500 flex-shrink-0" />}
                              {item.status === 'processing' && <Loader2 size={16} className="text-cyber-accent animate-spin flex-shrink-0" />}
                              {item.status === 'completed' && <CheckCircle2 size={16} className="text-cyber-success flex-shrink-0" />}
                              {item.status === 'failed' && <AlertCircle size={16} className="text-red-500 flex-shrink-0" />}
                              <span className={`text-sm font-medium truncate ${selectedFileId === item.id ? 'text-slate-200' : 'text-slate-400 group-hover:text-slate-300'}`}>
                                {item.filename}
                              </span>
                            </div>
                            <ChevronRight size={16} className={`flex-shrink-0 ${selectedFileId === item.id ? 'text-cyber-accent' : 'text-slate-600'}`} />
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Detail: Intelligence Workspace (70%) */}
                    <div className="w-[70%] glassmorphism rounded-xl flex flex-col overflow-hidden relative border border-white/10">
                      {selectedFileItem ? (
                        <>
                          {/* Header */}
                          <div className="p-5 border-b border-cyber-border bg-black/20 flex justify-between items-start backdrop-blur-md">
                            <div className="max-w-[70%]">
                              <h2 className="text-xl font-bold text-slate-100 mb-1">{selectedFileItem.filename}</h2>
                              <div className="flex items-center gap-2 text-sm">
                                <span className={`px-2 py-0.5 rounded-full border text-xs font-semibold uppercase tracking-wider
                              ${selectedFileItem.status === 'queued' ? 'bg-slate-800/80 border-slate-600 text-slate-400' :
                                    selectedFileItem.status === 'processing' ? 'bg-cyber-accent/20 border-cyber-accent text-cyber-accent' :
                                      selectedFileItem.status === 'completed' ? 'bg-cyber-success/20 border-cyber-success text-cyber-success' :
                                        'bg-red-500/20 border-red-500 text-red-500'}`}
                                >
                                  {selectedFileItem.status}
                                </span>
                                <span className="text-slate-400 flex items-center gap-1 bg-black/30 px-2 py-0.5 rounded-full">
                                  <Search size={14} /> {selectedFileItem.policies.length} Policies Matched
                                </span>
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div>
                              {selectedFileItem.status === 'queued' && (
                                <button
                                  className="cyber-button py-1.5 px-4 text-sm flex items-center gap-2"
                                  onClick={() => startAudit(selectedFileItem.id)}
                                  disabled={isAnyProcessing}
                                >
                                  <PlayCircle size={18} /> Start Audit
                                </button>
                              )}
                              {selectedFileItem.status === 'processing' && (
                                <div className="flex items-center gap-2 text-cyber-accent text-sm font-medium bg-cyber-accent/10 px-4 py-1.5 rounded-full border border-cyber-accent/30">
                                  <Loader2 size={16} className="animate-spin" /> Analyzing Document...
                                </div>
                              )}
                              {/* UPDATED ACTION BUTTON: DOCX Generation */}
                              {selectedFileItem.status === 'completed' && (
                                <div className="flex gap-2">
                                  <button
                                    className="bg-[#10b981]/80 hover:bg-[#10b981] text-white border border-[#10b981] font-medium py-1.5 px-4 rounded-lg flex items-center gap-2 transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                                    onClick={() => dispatchAudit(selectedFileItem.filename, selectedFileItem.memo)}
                                    disabled={isDispatching}
                                  >
                                    {isDispatching ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                                    {isDispatching ? 'Dispatching...' : 'Dispatch Audit'}
                                  </button>
                                  <button
                                    className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-600 font-medium py-1.5 px-4 rounded-lg flex items-center gap-2 transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                                    onClick={() => downloadDocx(selectedFileItem.filename, selectedFileItem.memo)}
                                    disabled={isGeneratingDocx}
                                  >
                                    {isGeneratingDocx ? <Loader2 size={18} className="animate-spin text-cyber-glow" /> : <FileDown size={18} className="text-cyber-glow" />}
                                    {isGeneratingDocx ? 'Compiling DOCX...' : 'Export DOCX'}
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Workspace Content */}
                          <div className="flex-1 flex flex-col overflow-hidden bg-black/20">

                            {/* Context Strip */}
                            {selectedFileItem.policies.length > 0 && (
                              <div className="px-5 py-3 border-b border-cyber-border/50 bg-[#151b2b]/40">
                                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Context Sources</span>
                                <div className="flex flex-wrap gap-2">
                                  {selectedFileItem.policies.map((pol, pidx) => (
                                    <span key={pidx} className="text-xs bg-slate-800/80 border border-slate-700 rounded px-2 py-1 text-slate-300">{pol}</span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Terminal Area / Markdown Output */}
                            <div className="flex-1 p-8 overflow-y-auto">
                              {selectedFileItem.memo ? (
                                <div className="markdown-body">
                                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {selectedFileItem.memo}
                                  </ReactMarkdown>
                                  {selectedFileItem.status === 'processing' && <span className="typewriter-cursor ml-2 mt-4"></span>}
                                </div>
                              ) : (
                                <div className="h-full flex flex-col items-center justify-center text-slate-500 font-sans gap-4">
                                  <BrainCircuit size={48} className="text-slate-700 opacity-50" />
                                  <p className="text-center max-w-md">
                                    {selectedFileItem.status === 'queued'
                                      ? "Click 'Start Audit' to cross-reference this document against ChromaDB context and generate the compliance memo."
                                      : "Starting DeepSeek-R1 reasoning engine..."}
                                  </p>
                                </div>
                              )}
                            </div>

                          </div>
                        </>
                      ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-4 bg-black/20 backdrop-blur-sm">
                          <FileIcon size={48} className="text-slate-700 opacity-50" />
                          <p>Select a document from the queue to view details</p>
                        </div>
                      )}
                    </div>

                  </div>
                )}

                {batchStatus === 'idle' && queue.length === 0 && (
                  <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-cyber-border/50 bg-black/20 backdrop-blur-md rounded-xl mt-8 opacity-70">
                    <FolderSearch size={48} className="text-slate-500 mb-4" />
                    <p className="text-slate-300 font-medium">Scan folder to populate the queue.</p>
                  </div>
                )}
              </div>
            )}

            {/* --- TAB 2: ON-DEMAND AUDIT --- */}
            {activeTab === 'ondemand' && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto w-full">
                <div className="text-center mb-10">
                  <h2 className="text-3xl font-bold text-slate-100 mb-2">Manual Document Upload</h2>
                  <p className="text-slate-400">Upload a single PDF notice to immediately cross-reference with ChromaDB and stream reasoning.</p>
                </div>

                <div className="flex flex-col items-center mb-10">
                  <div
                    className={`w-full max-w-2xl border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200 ${isDragging ? 'border-cyber-accent bg-cyber-accent/10' : file ? 'border-cyber-accent bg-cyber-accent/5' : 'border-cyber-border bg-cyber-panel/50 hover:border-cyber-accent hover:bg-cyber-accent/5'}`}
                    onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
                    onClick={() => document.getElementById('file-upload').click()}
                  >
                    <input type="file" id="file-upload" accept=".pdf" onChange={handleFileChange} className="hidden" />

                    {file ? (
                      <div className="flex flex-col items-center gap-2">
                        <FileIcon className="text-cyber-glow mb-2" size={48} />
                        <p className="font-semibold text-lg text-slate-200">{file.name}</p>
                        <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        <button
                          className="mt-4 text-xs border border-slate-600 hover:border-slate-400 px-3 py-1.5 rounded-lg transition-colors"
                          onClick={(e) => { e.stopPropagation(); setFile(null); setStatus('idle'); setPolicies([]); setStreamText(''); }}
                        >
                          Remove File
                        </button>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-3">
                        <UploadCloud className="text-cyber-accent mb-2" size={48} />
                        <h3 className="text-lg font-medium text-slate-200">Upload Government Notice</h3>
                        <p className="text-slate-400 text-sm">Drag & drop your PDF file here, or click to browse</p>
                      </div>
                    )}
                  </div>

                  <div className="mt-8">
                    <button
                      className="cyber-button flex items-center gap-2 text-lg"
                      onClick={runOnDemandAudit}
                      disabled={!file || (status !== 'idle' && status !== 'complete')}
                    >
                      {status === 'analyzing_db' ? <><Loader2 className="animate-spin" size={20} /> Analyzing Vector DB...</> :
                        status === 'streaming_ai' ? <><Loader2 className="animate-spin" size={20} /> Running AI Audit...</> :
                          status === 'complete' ? <><CheckCircle2 size={20} /> Audit Complete</> :
                            <>Run RegAI Audit</>}
                    </button>
                  </div>
                </div>

                {/* Results Grid */}
                {(status !== 'idle' || policies.length > 0 || streamText) && (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px] animate-in fade-in zoom-in-95 duration-500">
                    {/* Left Column: Context */}
                    <div className="cyber-panel rounded-xl flex flex-col overflow-hidden">
                      <div className="p-4 border-b border-cyber-border bg-white/5 flex items-center gap-3">
                        <Database size={18} className="text-cyber-accent" />
                        <h3 className="font-semibold text-slate-200">Retrieved Policies</h3>
                      </div>
                      <div className="p-5 flex-1 overflow-y-auto">
                        {status === 'analyzing_db' && policies.length === 0 ? (
                          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
                            <Loader2 className="animate-spin" size={24} />
                            <p>Querying ChromaDB...</p>
                          </div>
                        ) : policies.length > 0 ? (
                          <ul className="space-y-3">
                            {policies.map((policy, idx) => (
                              <li key={idx} className="flex items-start gap-3 p-3 bg-white/5 rounded-lg border-l-4 border-cyber-accent text-sm text-slate-300">
                                {policy}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="h-full flex items-center justify-center text-slate-500">No policies retrieved.</div>
                        )}
                      </div>
                    </div>

                    {/* Right Column: AI Engine */}
                    <div className="glassmorphism rounded-xl lg:col-span-2 flex flex-col overflow-hidden">
                      <div className="p-4 border-b border-white/10 bg-black/20 flex justify-between items-center backdrop-blur-md">
                        <div className="flex items-center gap-3">
                          <BrainCircuit size={18} className="text-cyber-glow" />
                          <h3 className="font-semibold text-slate-200">AI Reasoning Engine</h3>
                        </div>
                        {status === 'streaming_ai' && (
                          <div className="flex gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-cyber-accent animate-bounce" style={{ animationDelay: '-0.3s' }}></div>
                            <div className="w-1.5 h-1.5 rounded-full bg-cyber-accent animate-bounce" style={{ animationDelay: '-0.15s' }}></div>
                            <div className="w-1.5 h-1.5 rounded-full bg-cyber-accent animate-bounce"></div>
                          </div>
                        )}

                        {/* UPDATED ACTION BUTTON: DOCX Generation */}
                        {status === 'complete' && file && (
                          <div className="flex gap-2">
                            <button
                              className="bg-[#10b981]/80 hover:bg-[#10b981] text-white border border-[#10b981] font-medium py-1 px-3 text-sm rounded-lg flex items-center gap-2 transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                              onClick={() => dispatchAudit(file.name, streamText)}
                              disabled={isDispatching}
                            >
                              {isDispatching ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                              {isDispatching ? 'Dispatching...' : 'Dispatch Audit'}
                            </button>
                            <button
                              className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-600 font-medium py-1 px-3 text-sm rounded-lg flex items-center gap-2 transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                              onClick={() => downloadDocx(file.name, streamText)}
                              disabled={isGeneratingDocx}
                            >
                              {isGeneratingDocx ? <Loader2 size={16} className="animate-spin text-cyber-glow" /> : <FileDown size={16} className="text-cyber-glow" />}
                              {isGeneratingDocx ? 'Compiling DOCX...' : 'Export DOCX'}
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="p-6 flex-1 overflow-y-auto bg-black/20">
                        {streamText ? (
                          <div className="markdown-body">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {streamText}
                            </ReactMarkdown>
                            {status === 'streaming_ai' && <span className="typewriter-cursor ml-2"></span>}
                            <div ref={terminalEndRef} />
                          </div>
                        ) : (
                          <div className="h-full flex items-center justify-center text-slate-500 font-sans">
                            {status === 'analyzing_db' ? 'Waiting for context retrieval...' : 'Ready for AI stream.'}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* --- TAB 3: RECIPIENT MANAGER --- */}
            {activeTab === 'recipients' && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl mx-auto w-full">
                <div className="text-center mb-10">
                  <h2 className="text-3xl font-bold text-slate-100 mb-2 flex items-center justify-center gap-3">
                    <Mail className="text-cyber-accent" /> Communication Center
                  </h2>
                  <p className="text-slate-400">Manage employee distribution lists for automated compliance memo dispatches.</p>
                </div>

                <div className="glassmorphism rounded-2xl p-8 border border-white/10 shadow-2xl">
                  {/* Add Recipient Form */}
                  <form onSubmit={addRecipient} className="flex gap-4 mb-8">
                    <div className="flex-1 relative">
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                      <input 
                        type="email" 
                        required
                        placeholder="employee@company.com" 
                        className="w-full bg-black/40 border border-cyber-border rounded-xl py-3 pl-12 pr-4 text-slate-200 focus:outline-none focus:border-cyber-accent focus:ring-1 focus:ring-cyber-accent transition-all"
                        value={newEmail}
                        onChange={(e) => setNewEmail(e.target.value)}
                      />
                    </div>
                    <button type="submit" className="cyber-button flex items-center gap-2 px-6">
                      <Plus size={20} /> Add Employee
                    </button>
                  </form>

                  {/* Recipients List */}
                  <div className="bg-black/20 rounded-xl border border-white/5 overflow-hidden">
                    <div className="p-4 bg-white/5 border-b border-white/5 flex items-center justify-between">
                      <h3 className="font-semibold text-slate-200">Registered Recipients</h3>
                      <span className="bg-slate-800 text-slate-300 text-xs px-2.5 py-1 rounded-full font-medium">
                        {recipients.length} Total
                      </span>
                    </div>
                    
                    {recipients.length > 0 ? (
                      <ul className="divide-y divide-white/5 max-h-[400px] overflow-y-auto">
                        {recipients.map((email, idx) => (
                          <li key={idx} className="p-4 flex items-center justify-between hover:bg-white/5 transition-colors group">
                            {editingEmail === email ? (
                              <div className="flex-1 flex items-center gap-3">
                                <Mail className="text-slate-500" size={18} />
                                <input 
                                  type="email"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  className="bg-black/50 border border-cyber-accent rounded px-3 py-1.5 text-slate-200 text-sm w-full max-w-sm focus:outline-none"
                                  autoFocus
                                />
                                <div className="flex gap-2 ml-auto">
                                  <button onClick={() => saveEdit(email)} className="text-[#10b981] hover:bg-[#10b981]/20 p-1.5 rounded transition">
                                    <Check size={18} />
                                  </button>
                                  <button onClick={cancelEdit} className="text-red-400 hover:bg-red-400/20 p-1.5 rounded transition">
                                    <X size={18} />
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <>
                                <div className="flex items-center gap-3 text-slate-300">
                                  <div className="w-8 h-8 rounded-full bg-cyber-accent/20 flex items-center justify-center text-cyber-accent font-bold text-sm">
                                    {email.charAt(0).toUpperCase()}
                                  </div>
                                  {email}
                                </div>
                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button 
                                    onClick={() => startEdit(email)}
                                    className="text-slate-500 hover:text-cyber-accent p-2 rounded-lg hover:bg-cyber-accent/10 transition-colors"
                                    title="Edit Recipient"
                                  >
                                    <Edit2 size={18} />
                                  </button>
                                  <button 
                                    onClick={() => deleteRecipient(email)}
                                    className="text-slate-500 hover:text-red-400 p-2 rounded-lg hover:bg-red-400/10 transition-colors"
                                    title="Remove Recipient"
                                  >
                                    <Trash2 size={18} />
                                  </button>
                                </div>
                              </>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="p-12 text-center text-slate-500 flex flex-col items-center gap-3">
                        <Users size={48} className="opacity-30" />
                        <p>No recipients added yet. Add an email above to start building your distribution list.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* --- TAB 4: ASK RegAI CHATBOT --- */}
            {activeTab === 'chat' && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl mx-auto w-full h-[700px] flex flex-col">
                <div className="text-center mb-6">
                  <h2 className="text-3xl font-bold text-slate-100 mb-2 flex items-center justify-center gap-3">
                    <MessageSquare className="text-[#E03546]" /> Policy Concierge
                  </h2>
                  <p className="text-slate-400">Ask plain-English questions about corporate policies stored in Zomato DB.</p>
                </div>

                <div className="glassmorphism rounded-2xl border border-white/10 shadow-2xl flex-1 flex flex-col overflow-hidden bg-black/40">
                  <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {chatMessages.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-4">
                        <BrainCircuit size={64} className="opacity-20 text-[#E03546]" />
                        <p>How can I help you with our corporate policies today?</p>
                      </div>
                    ) : (
                      chatMessages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] rounded-2xl p-4 shadow-lg ${
                            msg.role === 'user' 
                              ? 'bg-cyber-accent/20 border border-cyber-accent/30 text-slate-200 rounded-tr-sm'
                              : 'bg-white/5 border border-[#E03546]/30 text-slate-300 rounded-tl-sm'
                          }`}>
                            <div className="flex items-center gap-2 mb-2">
                              {msg.role === 'user' ? (
                                <>
                                  <span className="text-xs font-bold text-cyber-accent uppercase tracking-wider">You</span>
                                  <Users size={14} className="text-cyber-accent" />
                                </>
                              ) : (
                                <>
                                  <Shield size={14} className="text-[#E03546]" />
                                  <span className="text-xs font-bold text-[#E03546] uppercase tracking-wider">RegAI</span>
                                </>
                              )}
                            </div>
                            <p className="leading-relaxed text-sm whitespace-pre-wrap">{msg.text}</p>
                          </div>
                        </div>
                      ))
                    )}
                    {isTyping && (
                      <div className="flex justify-start">
                        <div className="max-w-[80%] rounded-2xl p-4 shadow-lg bg-white/5 border border-[#E03546]/30 text-slate-300 rounded-tl-sm">
                          <div className="flex items-center gap-2 mb-2">
                            <Shield size={14} className="text-[#E03546]" />
                            <span className="text-xs font-bold text-[#E03546] uppercase tracking-wider">RegAI</span>
                          </div>
                          <div className="flex items-center gap-1.5 h-5">
                            <div className="w-1.5 h-1.5 rounded-full bg-[#E03546] animate-bounce" style={{ animationDelay: '-0.3s' }}></div>
                            <div className="w-1.5 h-1.5 rounded-full bg-[#E03546] animate-bounce" style={{ animationDelay: '-0.15s' }}></div>
                            <div className="w-1.5 h-1.5 rounded-full bg-[#E03546] animate-bounce"></div>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  
                  <div className="p-4 bg-white/5 border-t border-white/5">
                    <form onSubmit={handleSendMessage} className="flex gap-3">
                      <input 
                        type="text" 
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="Ask about leave policies, compliance deadlines, etc..." 
                        className="flex-1 bg-black/50 border border-cyber-border rounded-xl py-3 px-5 text-slate-200 focus:outline-none focus:border-[#E03546] focus:ring-1 focus:ring-[#E03546] transition-all"
                      />
                      <button 
                        type="submit" 
                        disabled={!chatInput.trim() || isTyping}
                        className="bg-[#E03546]/90 hover:bg-[#E03546] text-white px-6 rounded-xl font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-[0_0_15px_rgba(224,53,70,0.4)]"
                      >
                        <Send size={18} />
                        Send
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            )}
          </main>
        </>
      ) : (
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 pb-8 flex flex-col">
          <div className="animate-in fade-in zoom-in-95 duration-500 w-full mt-6">
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-slate-100 mb-2 flex items-center gap-3">
                <Users className="text-[#10b981]" /> Employee Compliance Portal
              </h2>
              <p className="text-slate-400">Plain English summaries of recent regulatory changes and their direct impact on your role.</p>
            </div>

            {employeeLoading ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400 gap-4">
                <Loader2 size={48} className="animate-spin text-[#10b981]" />
                <p>Fetching latest compliance updates...</p>
              </div>
            ) : (
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Left Column (70%) */}
                <div className="lg:w-[70%] flex flex-col gap-6">
                  {employeeUpdates.length > 0 ? employeeUpdates.map((update, idx) => (
                    <div key={idx} className="bg-white/5 border border-white/10 rounded-xl p-6 shadow-lg backdrop-blur-sm">
                      <div className="flex justify-between items-start mb-4">
                        <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                          <FileIcon className="text-slate-400" /> {update.filename}
                        </h3>
                        <a
                          href={`http://127.0.0.1:5000/api/notices/${update.filename}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs bg-slate-800 border border-slate-600 text-slate-300 px-3 py-1.5 rounded-full hover:bg-slate-700 transition flex items-center gap-1"
                        >
                          View Original PDF <ArrowRight size={14} />
                        </a>
                      </div>

                      <div className="space-y-4">
                        <div className="bg-slate-800/50 p-4 rounded-lg border-l-4 border-blue-500">
                          <h4 className="text-sm font-bold text-blue-400 uppercase tracking-wider mb-1 flex items-center gap-2">
                            <Info size={16} /> What It Means
                          </h4>
                          <p className="text-slate-300 text-sm leading-relaxed">{update.summary}</p>
                        </div>
                        <div className="bg-[#E03546]/10 p-4 rounded-lg border-l-4 border-[#E03546]">
                          <h4 className="text-sm font-bold text-[#E03546] uppercase tracking-wider mb-1 flex items-center gap-2">
                            <AlertCircle size={16} /> Impact on Your Role
                          </h4>
                          <p className="text-slate-300 text-sm leading-relaxed">{update.impact}</p>
                        </div>
                        <div className="bg-[#10b981]/10 p-4 rounded-lg border-l-4 border-[#10b981]">
                          <h4 className="text-sm font-bold text-[#10b981] uppercase tracking-wider mb-1 flex items-center gap-2">
                            <CheckCircle2 size={16} /> Benefits
                          </h4>
                          <p className="text-slate-300 text-sm leading-relaxed">{update.benefits}</p>
                        </div>
                      </div>
                    </div>
                  )) : (
                    <div className="bg-white/5 border border-white/10 rounded-xl p-12 text-center text-slate-400">
                      <CheckCircle2 size={48} className="mx-auto mb-4 text-[#10b981] opacity-50" />
                      <p className="text-lg">You're all caught up! No new regulatory updates.</p>
                    </div>
                  )}
                </div>

                {/* Right Column (30%) */}
                <div className="lg:w-[30%]">
                  <div className="sticky top-24 bg-white/5 border border-white/10 rounded-xl p-5 shadow-lg backdrop-blur-sm">
                    <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-4 pb-3 border-b border-white/10">
                      <Zap className="text-amber-400" /> ⚡ Quick Action Flashes
                    </h3>
                    <div className="space-y-3">
                      {flashAlerts.length > 0 ? flashAlerts.map((alert, idx) => (
                        <div key={idx} className="bg-amber-400/10 border border-amber-400/30 p-3 rounded-lg flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0 animate-pulse"></div>
                          <p className="text-sm text-amber-200/90">{alert}</p>
                        </div>
                      )) : (
                        <div className="text-sm text-slate-500 text-center py-6">No flash alerts.</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      )}
    </div>
  );
}

export default App;