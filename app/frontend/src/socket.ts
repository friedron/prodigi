import { io } from "socket.io-client";
import { loadingControls } from "./loadingState";

const socket = io("http://localhost:5005");

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
