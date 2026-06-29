import { useState } from 'react';
import { api } from '../api/client';

export default function AiMappingAssistant({ project, entity, rows = [] }) {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const unmapped = rows.filter((r) => r.target_field && !r.source_field).map((r) => r.target_field);

  const ask = async (q) => {
    const text = (q || question).trim();
    if (!text) return;
    setBusy(true);
    setError('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setQuestion('');
    try {
      const reply = await api.aiAssistant(project.id, text, { unmapped_fields: unmapped, entity });
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: reply.answer,
          actions: reply.suggested_actions || [],
          refs: reply.references || [],
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card ai-assistant">
      <h3>Mapping assistant</h3>
      <p className="muted compact">
        Ask about unmapped fields, Kraken error codes, or transforms. AI suggests — you approve mappings.
      </p>
      <div className="chat-log">
        {messages.length === 0 && (
          <p className="muted">Try: &quot;What does KT-CT-10006 mean?&quot; or &quot;Why is accountType unmapped?&quot;</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            <p>{m.text}</p>
            {m.refs?.length > 0 && <p className="muted small">Refs: {m.refs.join(', ')}</p>}
            {m.actions?.length > 0 && (
              <ul className="compact-list">
                {m.actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {error && <p className="alert error compact">{error}</p>}
      <div className="toolbar-row">
        <input
          className="flex-grow"
          placeholder="Ask about mapping, errors, transforms…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !busy && ask()}
        />
        <button type="button" className="btn primary" disabled={busy} onClick={() => ask()}>
          {busy ? '…' : 'Ask'}
        </button>
      </div>
    </div>
  );
}
