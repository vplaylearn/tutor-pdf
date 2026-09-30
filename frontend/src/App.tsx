import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import './styles.css';
import TextToSpeech from './TextToSpeech';

// Empty string => same-origin (/api/... on Vercel). Override for local dev via VITE_API_URL.
const API = import.meta.env.VITE_API_URL ?? '';

type Doc = {
  document_id: string;
  filename: string;
  title: string;
  pages: number;
  records: number;
  extraction_mode: string;
  status: string;
};

type Block = {
  heading?: string | null;
  text: string;
};

type Source = {
  document_id: string;
  question_number?: number | null;
  question: string;
  text: string;
  answer: string;
  answer_blocks: Block[];
  page?: number | null;
  page_start?: number | null;
  page_end?: number | null;
  score: number;
  match_type: string;
};

/* ---------------- Speech Recognition types ---------------- */

type SpeechRecognitionResultEvent = Event & {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
    };
  };
};

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;

  start: () => void;
  stop: () => void;

  onresult:
    | ((event: SpeechRecognitionResultEvent) => void)
    | null;

  onerror:
    | ((event: Event) => void)
    | null;

  onend:
    | (() => void)
    | null;
};

type SpeechRecognitionConstructor =
  new () => SpeechRecognitionInstance;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

/* ---------------------------------------------------------- */

export default function App() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [did, setDid] = useState('');
  const [q, setQ] = useState('');
  const [ans, setAns] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  // Speech state
  const [listening, setListening] = useState(false);

  const recognitionRef =
    useRef<SpeechRecognitionInstance | null>(null);

  const load = async () => {
    const r = await fetch(API + '/api/documents');
    const d = await r.json();

    setDocs(d);

    if (!did && d.length) {
      setDid(d[0].document_id);
    }
  };

  useEffect(() => {
    load().catch(e => setMsg(e.message));
  }, []);

  /* ---------------- Upload ---------------- */

  const upload = async (f: File) => {
    setBusy(true);
    setMsg('');

    try {
      const fd = new FormData();

      fd.append('file', f);

      const r = await fetch(
        API + '/api/documents/upload',
        {
          method: 'POST',
          body: fd
        }
      );

      const d = await r.json();

      if (!r.ok) {
        throw Error(d.detail);
      }

      await load();

      setDid(d.document_id);

      setMsg(`${d.filename} is ready.`);
    } catch (e) {
      setMsg(
        e instanceof Error
          ? e.message
          : 'Upload failed.'
      );
    } finally {
      setBusy(false);
    }
  };

  /* ---------------- Speech-to-text ---------------- */

  const startSpeech = () => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setMsg(
        'Speech recognition is not supported by this browser.'
      );

      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;

    // Indian English.
    // Change to "en-US" if you prefer.
    recognition.lang = 'en-IN';

    recognition.onresult = event => {
      let transcript = '';

      for (
        let i = 0;
        i < Object.keys(event.results).length;
        i++
      ) {
        const result = event.results[i];

        if (result?.[0]?.transcript) {
          transcript += result[0].transcript;
        }
      }

      if (transcript.trim()) {
        setQ(transcript.trim());
      }
    };

    recognition.onerror = () => {
      setListening(false);

      setMsg(
        'Speech recognition failed. Please try again.'
      );
    };

    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;

    setMsg('Listening...');
    setListening(true);

    recognition.start();
  };

  const stopSpeech = () => {
    recognitionRef.current?.stop();

    recognitionRef.current = null;
    setListening(false);

    setMsg('');
  };

  const toggleSpeech = () => {
    if (listening) {
      stopSpeech();
    } else {
      startSpeech();
    }
  };

  /* ---------------- Ask ---------------- */

  const ask = async (e: FormEvent) => {
    e.preventDefault();

    if (!did || !q.trim()) {
      return;
    }

    // Stop speech if still active
    if (listening) {
      stopSpeech();
    }

    setBusy(true);
    setAns('');
    setSources([]);
    setMsg('');

    try {
      const r = await fetch(
        API + '/api/doubt',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            document_id: did,
            question: q
          })
        }
      );

      const d = await r.json();

      if (!r.ok) {
        throw Error(d.detail);
      }

      setAns(d.answer);
      setSources(d.sources);
    } catch (e) {
      setMsg(
        e instanceof Error
          ? e.message
          : 'Question failed.'
      );
    } finally {
      setBusy(false);
    }
  };

  /* ---------------- UI ---------------- */

  return (
    <div className="app">

      <header>
        <h1>Local PDF Tutor</h1>

        <p>
          Multiple PDFs • Local search • No cloud
        </p>
      </header>

      <main>

        {/* Upload */}

        <section className="card">

          <h2>Upload PDF</h2>

          <input
            type="file"
            accept="application/pdf,.pdf"
            disabled={busy}
            onChange={e => {
              const f = e.target.files?.[0];

              if (f) {
                upload(f);
              }
            }}
          />

          {msg && (
            <p className="msg">
              {msg}
            </p>
          )}

        </section>


        {/* Question */}

        <section className="card">

          <h2>Ask a Question</h2>

          {docs.length ? (
            <>

              <select
                value={did}
                onChange={e => {
                  setDid(e.target.value);

                  setAns('');
                  setSources([]);
                }}
              >
                {docs.map(d => (
                  <option
                    key={d.document_id}
                    value={d.document_id}
                  >
                    {d.filename}
                  </option>
                ))}
              </select>


              {/* Question input + microphone */}

              <div className="question-box">

                <textarea
                  rows={5}
                  value={q}
                  onChange={e =>
                    setQ(e.target.value)
                  }
                  placeholder={
                    listening
                      ? 'Listening...'
                      : 'Ask a question about the selected PDF...'
                  }
                />

                <button
                  type="button"
                  className={
                    listening
                      ? 'mic-button listening'
                      : 'mic-button'
                  }
                  onClick={toggleSpeech}
                  disabled={busy}
                >
                  {listening
                    ? '■ Stop'
                    : '🎤 Speak'}
                </button>

              </div>


              <button
                disabled={busy || !q.trim()}
                onClick={ask}
              >
                {busy
                  ? 'Working...'
                  : 'Ask'}
              </button>

            </>
          ) : (
            <p>
              Upload a PDF first.
            </p>
          )}

        </section>


        {/* Answer */}

        {ans && (

          <section className="card">

            <h2>Answer</h2>

            <div className="answer">
              {ans}
            </div>

            <TextToSpeech
               text={ans}
                autoPlay={false}
             />

            {sources.map((s, i) => (

              <article
                className="source"
                key={i}
              >

                <h3>
                  Source
                  {s.question_number
                    ? ` — Question ${s.question_number}`
                    : ''}
                </h3>


                {s.question && (
                  <p>
                    {s.question}
                  </p>
                )}


                <p className="muted">

                  Pages{' '}

                  {s.page_start === s.page_end
                    ? s.page_start
                    : `${s.page_start}–${s.page_end}`}

                </p>


                {s.answer_blocks.map(
                  (b, j) => (

                    <div key={j}>

                      {b.heading && (
                        <h4>
                          {b.heading}
                        </h4>
                      )}

                      <p>
                        {b.text}
                      </p>

                    </div>

                  )
                )}


              </article>

            ))}

          </section>

        )}

      </main>

    </div>
  );
}