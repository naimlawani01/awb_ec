// ─────────────────────────────────────────────────────────────────────────────
// Railway Function — Envoi planifié du rapport d'activité Elite Cargo
//
// Cette fonction légère ne fait QU'UNE chose : appeler l'API backend qui, elle,
// génère le PDF et l'envoie par email. Aucun accès direct à la base ni au SMTP ici.
//
// À configurer dans le service Railway Function :
//   • Variables d'environnement :
//       BACKEND_URL  = https://<ton-backend>.up.railway.app   (sans slash final)
//       CRON_TOKEN   = <la même valeur que REPORT_CRON_TOKEN côté backend>
//       PERIOD       = last_week   (ou "last_month" pour le service mensuel)
//   • Cron Schedule :
//       hebdo   → 0 7 * * 1     (lundi 07:00 UTC = 07:00 Conakry)
//       mensuel → 0 7 1 * *     (le 1er à 07:00)  + mettre PERIOD=last_month
// ─────────────────────────────────────────────────────────────────────────────

const BASE = (process.env.BACKEND_URL || "").replace(/\/+$/, "");
const TOKEN = process.env.CRON_TOKEN || "";
const PERIOD = process.env.PERIOD || "last_week";

if (!BASE || !TOKEN) {
  console.error("BACKEND_URL et CRON_TOKEN sont requis.");
  process.exit(1);
}

const url = `${BASE}/api/v1/reports/cron/send?period=${encodeURIComponent(PERIOD)}`;

const res = await fetch(url, {
  method: "POST",
  headers: { "X-Cron-Token": TOKEN },
});

const body = await res.text();
console.log(`[rapport ${PERIOD}] HTTP ${res.status} → ${body}`);

if (!res.ok) {
  process.exit(1);
}
