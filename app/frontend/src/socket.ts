import { io } from "socket.io-client";
import { loadingControls } from "./loadingState";

const SESSION_KEY = "session_token";

const socket = io("http://localhost:5005", {
    // Sent on every (re)connect so the server can give this tab its session back,
    // or the last session left (see saveUiState) if this tab doesn't have one yet.
    auth: (cb) => cb({
        session: sessionStorage.getItem(SESSION_KEY),
        last: localStorage.getItem(SESSION_KEY),
    }),
});

socket.on("session", ({ token }: { token: string }) => {
    sessionStorage.setItem(SESSION_KEY, token);
});

// Every request the app sends, and every reply the server sends back,
// is treated as activity for the global loading indicator - see loadingState.ts.
const rawEmit = socket.emit.bind(socket);
socket.emit = ((event: string, ...args: unknown[]) => {
    loadingControls.notifyActivity();
    return rawEmit(event, ...args);
}) as typeof socket.emit;

socket.onAny(() => {
    loadingControls.notifyActivity();
});

socket.on("error", () => {
    loadingControls.forceHide();
});

export default socket;
