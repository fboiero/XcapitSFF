import { useState, useRef, useEffect } from 'react';
import Topbar from '../components/layout/Topbar';
import { assistant } from '../services/api';
import { Send, Sparkles, User, Loader2 } from 'lucide-react';

export default function SofiPage() {
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState(['mostrame los leads', 'ver dashboard', 'crear ticket urgente', 'ayuda']);
  const scrollRef = useRef(null);

  useEffect(() => {
    // Create conversation on mount
    assistant.createConversation()
      .then(res => {
        setConvId(res.conversation_id);
        if (res.message) {
          setMessages([{ role: 'assistant', content: res.message.content, visual: res.message.visual, suggestions: res.message.suggestions }]);
          if (res.message.suggestions) setSuggestions(res.message.suggestions);
        }
      })
      .catch(() => {
        setMessages([{ role: 'assistant', content: 'Hola! Soy Sofi. No pude conectar con el backend, pero estoy lista para cuando se conecte.' }]);
      });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function sendMessage(text) {
    if (!text.trim() || !convId) return;
    const userMsg = { role: 'user', content: text };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await assistant.sendMessage(convId, text);
      const botMsg = {
        role: 'assistant',
        content: res.content || res.message?.content || JSON.stringify(res),
        visual: res.visual || res.message?.visual,
        suggestions: res.suggestions || res.message?.suggestions,
      };
      setMessages(m => [...m, botMsg]);
      if (botMsg.suggestions) setSuggestions(botMsg.suggestions);
    } catch (err) {
      setMessages(m => [...m, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function renderVisual(visual) {
    if (!visual) return null;
    if (visual.type === 'table' && visual.data?.leads) {
      return (
        <div className="mt-2 rounded-lg overflow-hidden border border-[#2d3748] text-xs">
          <table className="w-full">
            <thead><tr className="bg-[#1e2432]">
              <th className="px-2 py-1.5 text-left text-slate-500">Empresa</th>
              <th className="px-2 py-1.5 text-left text-slate-500">Score</th>
              <th className="px-2 py-1.5 text-left text-slate-500">Stage</th>
            </tr></thead>
            <tbody>
              {visual.data.leads.map((l, i) => (
                <tr key={i} className="border-t border-[#2d3748]">
                  <td className="px-2 py-1.5 text-white">{l.company}</td>
                  <td className="px-2 py-1.5 text-amber-400">{l.score}</td>
                  <td className="px-2 py-1.5 text-slate-400">{l.stage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    if (visual.type === 'card' && visual.data) {
      return (
        <div className="mt-2 rounded-lg bg-black/20 p-3 text-xs space-y-1">
          {Object.entries(visual.data).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-slate-400">{k}</span>
              <span className="text-white font-medium">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  }

  return (
    <div className="flex flex-col h-screen">
      <Topbar title="Sofi — Asistente IA" subtitle="Consultá datos en lenguaje natural, conectada a datos reales" />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 animate-fade-in ${msg.role === 'user' ? 'flex-row-reverse' : ''}`} style={{ animationDelay: `${i * 50}ms` }}>
            <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center ${
              msg.role === 'user' ? 'bg-indigo-500' : 'bg-gradient-to-br from-indigo-500 to-purple-600'
            }`}>
              {msg.role === 'user' ? <User size={14} className="text-white" /> : <Sparkles size={14} className="text-white" />}
            </div>
            <div className={`max-w-[75%] rounded-xl px-4 py-3 ${
              msg.role === 'user' ? 'bg-indigo-500 text-white' : 'bg-[#1e2432] border border-[#2d3748] text-slate-200'
            }`}>
              <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
              {renderVisual(msg.visual)}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Sparkles size={14} className="text-white" />
            </div>
            <div className="bg-[#1e2432] border border-[#2d3748] rounded-xl px-4 py-3">
              <Loader2 size={16} className="animate-spin text-indigo-400" />
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Suggestions */}
      <div className="px-6 pb-2 flex gap-2 flex-wrap">
        {suggestions.slice(0, 4).map((s, i) => (
          <button
            key={i}
            onClick={() => sendMessage(s)}
            className="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-400 hover:bg-indigo-500/20 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-[#2d3748]">
        <form onSubmit={e => { e.preventDefault(); sendMessage(input); }} className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Escribí un mensaje para Sofi..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-[#1e2432] border border-[#2d3748] text-sm text-white placeholder:text-slate-600 focus:border-indigo-500/50 focus:outline-none transition-colors"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 rounded-xl bg-indigo-500 text-white text-sm font-medium hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
