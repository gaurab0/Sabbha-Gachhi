/**
 * TokenCheckPage — the /status-check route.
 *
 * This was a byte-identical duplicate of StatusPage.tsx. It now re-exports
 * the canonical component so both routes share one implementation and one
 * set of behaviors (details modal, withdraw dialog, verification gating).
 */
export { default } from "./StatusPage";
