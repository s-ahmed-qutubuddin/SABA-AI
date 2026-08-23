import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";
import { WS_URL, api } from "../services/api";
import { ConversationTurn, SabaState, WsEvent } from "../types";
import { WebResult } from "../components/web/WebResultsPanel";

interface VoiceStateValue {
  state: SabaState;
  connected: boolean;
  turns: ConversationTurn[];
  lastError: string | null;
  systemAction: string | null;
  webResults: WebResult[] | null;
  start: (activationId?: string) => Promise<void>;
  stop: () => Promise<void>;
  sendText: (text: string) => Promise<void>;
}

const VoiceStateContext = createContext<VoiceStateValue | null>(null);

const ACTIVATION_WS_URL = (
  import.meta.env.VITE_ACTIVATION_WS_URL ||
  "ws://localhost:8000/ws/activation"
).replace(/\/$/, "");

// Google recommends sending Live API audio in reasonably sized PCM chunks.
// 100 ms at 16 kHz = 1600 samples.
const OUTPUT_SAMPLE_RATE = 16000;
const AUDIO_CHUNK_SAMPLES = 1600;

function downsample(
  buffer: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number,
) {
  if (outputSampleRate === inputSampleRate) return buffer;
  const ratio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;

    for (
      let i = offsetBuffer;
      i < nextOffsetBuffer && i < buffer.length;
      i += 1
    ) {
      accum += buffer[i];
      count += 1;
    }

    result[offsetResult] = count ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function floatTo16BitPCM(float32: Float32Array) {
  const output = new Int16Array(float32.length);

  for (let i = 0; i < float32.length; i += 1) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  return output;
}

function appendFloat16Buffer(
  target: Int16Array,
  offset: number,
  source: Int16Array,
) {
  target.set(source, offset);
}

export function VoiceStateProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [state, setState] = useState<SabaState>("stopped");
  const [connected, setConnected] = useState(false);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);
  const [systemAction, setSystemAction] = useState<string | null>(null);
  const [webResults, setWebResults] = useState<WebResult[] | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const activationSocketRef = useRef<WebSocket | null>(null);
  const mediaRef = useRef<MediaStream | null>(null);
  const audioInputRef = useRef<AudioContext | null>(null);
  const audioOutputRef = useRef<AudioContext | null>(null);
  const workletRef = useRef<AudioWorkletNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const muteRef = useRef<GainNode | null>(null);
  const playbackTimeRef = useRef(0);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const audioBufferRef = useRef<Int16Array>(
    new Int16Array(AUDIO_CHUNK_SAMPLES),
  );
  const audioBufferLengthRef = useRef(0);
  const lastAudioSentAtRef = useRef(0);

  const activeRef = useRef(false);
  const stopRequestedRef = useRef(false);
  const startInProgressRef = useRef(false);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectingRef = useRef(false);
  const conversationIdRef = useRef<number | null>(null);
  const creatorSessionRef = useRef<string | null>(null);
  const activationIdRef = useRef<string | null>(null);
  const audioWatchdogRef = useRef<number | null>(null);
  const audioPrimedRef = useRef(false);
  const lastWorkletFrameAtRef = useRef(0);
  const inputRepairPromiseRef = useRef<Promise<void> | null>(null);

  const upsertTurn = useCallback(
    (role: "user" | "assistant", text: string) => {
      if (!text) return;

      setTurns((prev) => {
        const last = prev[prev.length - 1];

        if (last && last.role === role) {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              text: `${last.text}${text}`,
              at: Date.now(),
            },
          ];
        }

        return [
          ...prev,
          {
            role,
            text,
            at: Date.now(),
          },
        ];
      });
    },
    [],
  );

  const playPcm24k = useCallback(async (buffer: ArrayBuffer) => {
    const ctx =
      audioOutputRef.current ||
      new AudioContext({ latencyHint: "interactive" });

    audioOutputRef.current = ctx;

    if (ctx.state === "suspended") {
      await ctx.resume();
    }

    const samples = new Int16Array(buffer);
    const audio = ctx.createBuffer(1, samples.length, 24000);
    const channel = audio.getChannelData(0);

    for (let i = 0; i < samples.length; i += 1) {
      channel[i] = samples[i] / 32768;
    }

    const source = ctx.createBufferSource();
    source.buffer = audio;
    source.connect(ctx.destination);
    source.onended = () => {
      activeSourcesRef.current = activeSourcesRef.current.filter(
        (s) => s !== source,
      );
    };
    activeSourcesRef.current.push(source);

    const startAt = Math.max(
      ctx.currentTime + 0.015,
      playbackTimeRef.current,
    );

    source.start(startAt);
    playbackTimeRef.current = startAt + audio.duration;
  }, []);

  // Barge-in: stop every currently scheduled/playing output chunk immediately.
  // Without this, audio already queued on the output AudioContext keeps
  // playing even after Gemini reports the turn was interrupted.
  const stopPlayback = useCallback(() => {
    for (const source of activeSourcesRef.current) {
      try {
        source.stop();
      } catch {
        // Already stopped/ended; ignore.
      }
    }
    activeSourcesRef.current = [];
    playbackTimeRef.current = audioOutputRef.current?.currentTime ?? 0;
  }, []);

  const cleanupAudio = useCallback(() => {
    stopPlayback();
    workletRef.current?.disconnect();
    sourceRef.current?.disconnect();
    muteRef.current?.disconnect();

    workletRef.current = null;
    sourceRef.current = null;
    muteRef.current = null;

    mediaRef.current?.getTracks().forEach((track) => track.stop());
    mediaRef.current = null;

    void audioInputRef.current?.close();
    audioInputRef.current = null;

    void audioOutputRef.current?.close();
    audioOutputRef.current = null;

    playbackTimeRef.current = 0;
    audioBufferLengthRef.current = 0;
    inputRepairPromiseRef.current = null;
  }, [stopPlayback]);

  const buildVoiceUrl = useCallback(() => {
    const url = new URL(WS_URL);

    if (conversationIdRef.current) {
      url.searchParams.set(
        "conversation_id",
        String(conversationIdRef.current),
      );
    }

    if (activationIdRef.current) {
      url.searchParams.set(
        "activation_id",
        activationIdRef.current,
      );
    }

    if (creatorSessionRef.current) {
      url.searchParams.set(
        "creator_session_token",
        creatorSessionRef.current,
      );
    }

    return url.toString();
  }, []);

  const handleEvent = useCallback(
    (data: WsEvent) => {
      if (data.type === "state" && data.state) {
        setState(data.state);
      }

      if (data.type === "ready") {
        setLastError(null);
        setConnected(true);
        reconnectAttemptsRef.current = 0;

        const conversationId = data.conversation_id;
        if (typeof conversationId === "number") {
          conversationIdRef.current = conversationId;
        }

        const creatorSessionToken = data.creator_session_token;
        if (typeof creatorSessionToken === "string") {
          creatorSessionRef.current = creatorSessionToken;
        }
      }

      if (data.type === "transcript" && data.text) {
        upsertTurn("user", data.text);
      }

      if (data.type === "response" && data.text) {
        upsertTurn("assistant", data.text);
      }

      if (data.type === "tool_start" && data.name) {
        const labels: Record<string, string> = {
          remember: "Saving a memory",
          recall_memory: "Checking memory",
          identify_family_member: "Checking family identity",
          family_context: "Checking family context",
          create_note: "Creating a note",
          create_task: "Creating a task",
          set_preference: "Saving your preference",
          open_allowed_app: "Opening an app",
          set_volume: "Adjusting volume",
          get_volume: "Checking volume",
          media_control: "Controlling media",
          battery_status: "Checking battery",
          system_info: "Checking system information",
          clipboard_read: "Reading clipboard",
          clipboard_write: "Updating clipboard",
          open_url: "Opening a webpage",
          search_web: "Searching the web",
          get_weather: "Checking the weather",
          get_news: "Checking the news",
          calculate: "Calculating",
          activate_developer_mode: "Activating developer mode",
          developer_diagnostics: "Running diagnostics",
          open_project: "Opening the project",
          list_project: "Inspecting project files",
          git_status: "Checking project status",
          home_list_devices: "Checking connected appliances",
          home_find_device: "Finding your appliance",
          home_get_status: "Checking appliance status",
          home_get_capabilities: "Checking appliance capabilities",
          home_control_device: "Controlling the appliance",
          home_get_energy: "Checking appliance energy",
          home_estimate_cost: "Estimating electricity cost",
        };
        setSystemAction(labels[data.name] || "Working on it");
      }

      if (data.type === "tool_result" && data.name) {
        const result = data.result as
          | {
              label?: string;
              results?: WebResult[];
            }
          | undefined;

        setSystemAction(
          result?.label || `${data.name} complete`,
        );

        if (result?.results) {
          setWebResults(result.results);
        }
      }

      if (data.type === "error") {
        setLastError(
          data.message || "Voice connection error",
        );
      }

      if (data.type === "interrupted") {
        stopPlayback();
        setState("listening");
      }
    },
    [upsertTurn, stopPlayback],
  );

  const flushAudioBuffer = useCallback(() => {
    const length = audioBufferLengthRef.current;
    if (!length) return;

    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      audioBufferLengthRef.current = 0;
      return;
    }

    const pcm = audioBufferRef.current.slice(0, length);
    socket.send(pcm.buffer);
    audioBufferLengthRef.current = 0;
    lastAudioSentAtRef.current = Date.now();
  }, []);

  const enqueueAudio = useCallback(
    (samples: Int16Array) => {
      let sourceOffset = 0;

      while (sourceOffset < samples.length) {
        const capacity =
          AUDIO_CHUNK_SAMPLES -
          audioBufferLengthRef.current;

        const take = Math.min(
          capacity,
          samples.length - sourceOffset,
        );

        appendFloat16Buffer(
          audioBufferRef.current,
          audioBufferLengthRef.current,
          samples.subarray(
            sourceOffset,
            sourceOffset + take,
          ),
        );

        audioBufferLengthRef.current += take;
        sourceOffset += take;

        if (
          audioBufferLengthRef.current >=
          AUDIO_CHUNK_SAMPLES
        ) {
          flushAudioBuffer();
        }
      }
    },
    [flushAudioBuffer],
  );

  const ensureInputAudio = useCallback(async () => {
    if (inputRepairPromiseRef.current) {
      return inputRepairPromiseRef.current;
    }

    const repair = (async () => {
    const audioTracks = mediaRef.current?.getAudioTracks() ?? [];
    const hasLiveTrack = audioTracks.some((track) => track.readyState === "live");
    if (!hasLiveTrack) {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaRef.current = stream;
    }

    let ctx = audioInputRef.current;
    if (!ctx || ctx.state === "closed") {
      ctx = new AudioContext({ latencyHint: "interactive" });
      audioInputRef.current = ctx;
      audioPrimedRef.current = true;
    }

    if (ctx.state !== "running") {
      try {
        await ctx.resume();
      } catch {
        // Browser policy may require a user gesture; the watchdog retries.
      }
    }

    const graphContextMatches =
      !!workletRef.current &&
      !!sourceRef.current &&
      !!muteRef.current &&
      sourceRef.current.context === ctx &&
      muteRef.current.context === ctx &&
      workletRef.current.context === ctx;

    const graphIsStale =
      lastWorkletFrameAtRef.current > 0 &&
      performance.now() - lastWorkletFrameAtRef.current > 1800;

    const needsGraph = !graphContextMatches || graphIsStale;

    if (!needsGraph) return;

    workletRef.current?.disconnect();
    sourceRef.current?.disconnect();
    muteRef.current?.disconnect();
    workletRef.current = null;
    sourceRef.current = null;
    muteRef.current = null;

    const media = mediaRef.current;
    if (!media) {
      throw new Error("Microphone stream is unavailable. Please allow microphone access and try again.");
    }
    const source = ctx.createMediaStreamSource(media);
    sourceRef.current = source;

    const processorName = `saba-pcm-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const workletCode = `
      class PCMProcessor extends AudioWorkletProcessor {
        process(inputs) {
          const input = inputs[0]?.[0];
          if (input) this.port.postMessage(input.slice());
          return true;
        }
      }
      registerProcessor('${processorName}', PCMProcessor);
    `;

    const blobUrl = URL.createObjectURL(
      new Blob([workletCode], { type: "application/javascript" }),
    );

    await ctx.audioWorklet.addModule(blobUrl);
    URL.revokeObjectURL(blobUrl);

    const node = new AudioWorkletNode(ctx, processorName, {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      outputChannelCount: [1],
    });

    workletRef.current = node;
    lastWorkletFrameAtRef.current = performance.now();

    node.port.onmessage = (event: MessageEvent<Float32Array>) => {
      lastWorkletFrameAtRef.current = performance.now();

      const samples16k = downsample(
        event.data,
        ctx!.sampleRate,
        OUTPUT_SAMPLE_RATE,
      );

      enqueueAudio(floatTo16BitPCM(samples16k));
    };

    const mute = ctx.createGain();
    mute.gain.value = 0;
    muteRef.current = mute;
    source.connect(node).connect(mute).connect(ctx.destination);

    })();

    inputRepairPromiseRef.current = repair;
    try {
      await repair;
    } finally {
      if (inputRepairPromiseRef.current === repair) {
        inputRepairPromiseRef.current = null;
      }
    }
  }, [enqueueAudio]);

  const connectVoiceSocket = useCallback(async () => {
    if (!activeRef.current || stopRequestedRef.current) return;

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(buildVoiceUrl());
    ws.binaryType = "arraybuffer";
    socketRef.current = ws;
    reconnectingRef.current = true;

    await new Promise<void>((resolve, reject) => {
      ws.onopen = () => {
        reconnectingRef.current = false;
        resolve();
      };

      ws.onerror = () => {
        reconnectingRef.current = false;
        reject(
          new Error(
            "Could not connect to Saba voice service.",
          ),
        );
      };
    });

    setConnected(true);
    ws.send(JSON.stringify({ action: "start" }));

    ws.onmessage = async (event) => {
      if (typeof event.data === "string") {
        try {
          handleEvent(JSON.parse(event.data));
        } catch {
          // Ignore malformed events rather than killing the session.
        }
        return;
      }

      if (event.data instanceof ArrayBuffer) {
        setState("speaking");
        await playPcm24k(event.data);
        return;
      }

      if (event.data instanceof Blob) {
        setState("speaking");
        await playPcm24k(
          await event.data.arrayBuffer(),
        );
      }
    };

    ws.onclose = () => {
      // If a newer socket has already replaced this one (e.g. a reconnect already
      // succeeded), this is a stale close event from the old socket arriving late.
      // Previously this only bailed out when the session was also inactive, so a
      // late close from a replaced-but-still-active socket would incorrectly mark
      // the live connection as disconnected and could kick off a redundant
      // reconnect on top of the already-working one. Ignore it whenever it's not
      // the current socket, full stop.
      if (socketRef.current !== ws) return;

      socketRef.current = null;
      setConnected(false);

      if (
        activeRef.current &&
        !stopRequestedRef.current
      ) {
        if (reconnectTimerRef.current !== null) {
          window.clearTimeout(
            reconnectTimerRef.current,
          );
        }

        const attempt = reconnectAttemptsRef.current;
        reconnectAttemptsRef.current = attempt + 1;

        if (attempt < 12) {
          const delay = Math.min(
            1500 * Math.pow(1.35, attempt),
            8000,
          );

          reconnectTimerRef.current =
            window.setTimeout(() => {
              void connectVoiceSocket().catch(
                (error) => {
                  setLastError(
                    error instanceof Error
                      ? error.message
                      : "Voice reconnect failed.",
                  );
                },
              );
            }, delay);
        } else {
          setState("error");
          setLastError(
            "Voice session could not reconnect.",
          );
        }
      } else {
        setState("stopped");
      }
    };

    ws.onerror = () => {
      // onclose handles the reconnect lifecycle.
    };
  }, [buildVoiceUrl, handleEvent, playPcm24k]);

  const start = useCallback(
    async (activationId?: string) => {
      if (startInProgressRef.current) return;
      if (activeRef.current && socketRef.current?.readyState === WebSocket.OPEN) return;
      if (activeRef.current && socketRef.current && socketRef.current.readyState !== WebSocket.OPEN) {
        try { socketRef.current.close(); } catch { /* ignore stale socket */ }
        socketRef.current = null;
      }
      if (activeRef.current) {
        stopRequestedRef.current = false;
      }

      startInProgressRef.current = true;
      stopRequestedRef.current = false;
      activeRef.current = true;

      if (activationId) {
        activationIdRef.current = activationId;
      }

      setLastError(null);
      setSystemAction(null);
      setState("thinking");

      try {
        await ensureInputAudio();
        await connectVoiceSocket();
      } catch (error) {
        activeRef.current = false;
        stopRequestedRef.current = true;
        cleanupAudio();
        setConnected(false);
        setState("error");
        setLastError(
          error instanceof Error
            ? error.message
            : "Voice setup failed.",
        );
      } finally {
        startInProgressRef.current = false;
      }
    },
    [cleanupAudio, connectVoiceSocket, ensureInputAudio],
  );

  const stop = useCallback(async () => {
    stopRequestedRef.current = true;
    activeRef.current = false;
    startInProgressRef.current = false;

    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    flushAudioBuffer();

    try {
      socketRef.current?.send(
        JSON.stringify({ action: "stop" }),
      );
    } catch {
      // Ignore shutdown races.
    }

    socketRef.current?.close();
    socketRef.current = null;

    activationIdRef.current = null;
    cleanupAudio();
    setConnected(false);
    setState("stopped");
  }, [cleanupAudio, flushAudioBuffer]);

  const sendText = useCallback(
    async (text: string) => {
      const value = text.trim();
      if (!value) return;

      try {
        if (
          socketRef.current?.readyState ===
          WebSocket.OPEN
        ) {
          socketRef.current.send(
            JSON.stringify({
              action: "text",
              text: value,
            }),
          );
          return;
        }

        const result = await api.chat(
          conversationIdRef.current,
          value,
        );

        if (result.conversation_id) {
          conversationIdRef.current =
            result.conversation_id;
        }

        setTurns((prev) => [
          ...prev,
          {
            role: "user",
            text: value,
            at: Date.now(),
          },
          {
            role: "assistant",
            text: result.response,
            at: Date.now(),
          },
        ]);
      } catch (error) {
        setLastError(
          error instanceof Error
            ? error.message
            : "Chat request failed.",
        );
      }
    },
    [],
  );

  // Returning to LISTENING is a runtime guarantee, not just a UI state. Re-validate
  // the live mic graph whenever Gemini finishes a turn or reports listening.
  useEffect(() => {
    if (state !== "listening" || !activeRef.current || stopRequestedRef.current) return;
    void ensureInputAudio().catch((error) => {
      setLastError(error instanceof Error ? error.message : "Microphone recovery failed.");
    });
  }, [state, ensureInputAudio]);

  // Keep the real microphone pipeline alive while the UI may say LISTENING.
  useEffect(() => {
    const prime = () => {
      if (audioPrimedRef.current) return;
      audioPrimedRef.current = true;
      const existing = audioInputRef.current;
      const ctx = existing || new AudioContext({ latencyHint: "interactive" });
      audioInputRef.current = ctx;
      void ctx.resume();
    };
    window.addEventListener("pointerdown", prime, { once: true, passive: true });
    window.addEventListener("keydown", prime, { once: true });

    return () => {
      window.removeEventListener("pointerdown", prime);
      window.removeEventListener("keydown", prime);
    };
  }, [ensureInputAudio]);

  // The clap detector lives outside the browser's voice stream. This socket
  // receives only activation events, never raw microphone audio.
  useEffect(() => {
    let disposed = false;
    let reconnectTimer: number | null = null;
    let attempts = 0;

    const connectActivation = () => {
      if (disposed) return;

      const ws = new WebSocket(ACTIVATION_WS_URL);
      activationSocketRef.current = ws;

      ws.onopen = () => {
        attempts = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (
            data?.type === "clap_detected" &&
            typeof data.activation_id === "string"
          ) {
            void start(data.activation_id);
          }
        } catch {
          // Ignore malformed activation events.
        }
      };

      ws.onclose = () => {
        activationSocketRef.current = null;
        if (disposed) return;

        const delay = Math.min(
          1000 * Math.pow(1.4, attempts),
          8000,
        );
        attempts += 1;

        reconnectTimer = window.setTimeout(
          connectActivation,
          delay,
        );
      };
    };

    connectActivation();

    return () => {
      disposed = true;

      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }

      activationSocketRef.current?.close();
      activationSocketRef.current = null;
    };
  }, [start]);

  // Keep the microphone graph alive after every turn. Some browsers can suspend
  // an otherwise-silent AudioContext; resume it and send a small silence frame
  // so the same Live session remains active without requiring another button press.
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!activeRef.current || stopRequestedRef.current) return;

      const ctx = audioInputRef.current;
      if (ctx && ctx.state === "suspended") {
        void ctx.resume().catch(() => undefined);
      }

      // A browser can leave the UI in LISTENING while an AudioWorklet graph has
      // silently stopped producing frames. Re-run the graph health check and
      // rebuild it when the worker has been quiet too long.
      if (audioInputRef.current && lastWorkletFrameAtRef.current > 0) {
        const silentFor = performance.now() - lastWorkletFrameAtRef.current;
        if (silentFor > 1200) {
          void ensureInputAudio().catch((error) => {
            setLastError(error instanceof Error ? error.message : "Microphone recovery failed.");
          });
        }
      }

      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN) {
        const age = Date.now() - lastAudioSentAtRef.current;
        if (age > 1200) {
          const silence = new Int16Array(AUDIO_CHUNK_SAMPLES);
          socket.send(silence.buffer);
          lastAudioSentAtRef.current = Date.now();
        }
      }
    }, 750);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    return () => {
      activeRef.current = false;
      stopRequestedRef.current = true;

      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      activationSocketRef.current?.close();
      socketRef.current?.close();
      cleanupAudio();
    };
  }, [cleanupAudio]);

  return (
    <VoiceStateContext.Provider
      value={{
        state,
        connected,
        turns,
        lastError,
        systemAction,
        webResults,
        start,
        stop,
        sendText,
      }}
    >
      {children}
    </VoiceStateContext.Provider>
  );
}

export function useVoiceState() {
  const ctx = useContext(VoiceStateContext);

  if (!ctx) {
    throw new Error(
      "useVoiceState must be used within VoiceStateProvider",
    );
  }

  return ctx;
}
