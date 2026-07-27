import { reactive } from "vue";

// Any socket request/response activity keeps this active; it goes idle once
// the socket has been quiet for DEBOUNCE_MS. This is a best-effort fallback
// for actions with no precise completion signal to hook (e.g. endpoints that
// don't emit a reply yet) - components that DO know their exact response
// event should track completion themselves instead of relying on this timer,
// since a slow single request/response with no chatter in between will still
// look "done" once the window elapses even though the server is still working.
const DEBOUNCE_MS = 1500;

export const loadingState = reactive({
    active: false,
});

let hideTimer: ReturnType<typeof setTimeout> | undefined;

function notifyActivity() {
    loadingState.active = true;
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
        loadingState.active = false;
    }, DEBOUNCE_MS);
}

function forceHide() {
    clearTimeout(hideTimer);
    loadingState.active = false;
}

export const loadingControls = { notifyActivity, forceHide };
