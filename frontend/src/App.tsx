import { useEffect, useState } from 'react';
import { ChatInput } from './components/ChatInput';
import { ChatThread } from './components/ChatThread';
import { Header } from './components/Header';
import { PoliciesModal } from './components/PoliciesModal';
import { ChatMessage, HealthStatus, PolicyItem } from './types';

const API_BASE = (import.meta.env.VITE_API_URL || '')
  .replace(/\/+$/, '')
  .replace(/\/api$/, '');

export function App() {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [policies, setPolicies] = useState<PolicyItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPoliciesOpen, setIsPoliciesOpen] = useState(false);
  const [isReloading, setIsReloading] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const fetchHealth = async () => {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error(`Health check failed (${response.status})`);
    setHealth(await response.json() as HealthStatus);
  };

  const fetchPolicies = async () => {
    const response = await fetch(`${API_BASE}/api/policies`);
    if (!response.ok) throw new Error(`Policy registry failed (${response.status})`);
    setPolicies(await response.json() as PolicyItem[]);
  };

  useEffect(() => {
    void Promise.all([fetchHealth(), fetchPolicies()]).catch((error: unknown) => {
      const message = error instanceof Error ? error.message : 'Backend connection failed';
      setConnectionError(message);
    });
  }, []);

  const handleSendMessage = async (text: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((current) => [...current, { id: crypto.randomUUID(), sender: 'user', content: text, timestamp }]);
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });
      if (!response.ok) throw new Error(`Chat request failed (${response.status})`);
      const data = await response.json();
      setMessages((current) => [...current, {
        id: crypto.randomUUID(), sender: 'assistant', content: data.response,
        decision: data.decision, evidence: data.evidence, validation_passed: data.validation_passed, timestamp,
      }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to reach the backend';
      setMessages((current) => [...current, { id: crypto.randomUUID(), sender: 'assistant', content: `WeatherGuard is unavailable: ${message}`, timestamp }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewSession = () => {
    setSessionId(crypto.randomUUID());
    setMessages([]);
  };

  const handleReload = async () => {
    setIsReloading(true);
    try {
      const response = await fetch(`${API_BASE}/api/policies/reload`, { method: 'POST' });
      if (!response.ok) throw new Error(`Policy reload failed (${response.status})`);
      await fetchPolicies();
      await fetchHealth();
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : 'Policy reload failed');
    } finally {
      setIsReloading(false);
    }
  };

  return (
    <div className="app-container">
      <Header health={health} onNewSession={handleNewSession} onOpenPolicies={() => setIsPoliciesOpen(true)} />
      <main className="main-content">
        <section className="chat-panel">
          <ChatThread messages={messages} isLoading={isLoading} />
          <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
        </section>
      </main>
      <PoliciesModal isOpen={isPoliciesOpen} onClose={() => setIsPoliciesOpen(false)} policies={policies} onReload={handleReload} isReloading={isReloading} />
      {connectionError && <div className="connection-error" role="alert">Backend connection: {connectionError}</div>}
    </div>
  );
}

export default App;
