// ─────────────────────────────────────────────────────────────────────────────
// Railway Function — Envoi planifié du rapport d'activité Elite Cargo
// (index.tsx — runtime Bun. Script simple, exécuté de haut en bas, comme l'exemple.)
//
// ⚠️ EFFACE TOUT le contenu par défaut du fichier index.tsx (template "cat fact"
//    avec zod) et colle CE code à la place. Aucune dépendance, aucun import.
//
// Cette fonction ne fait qu'appeler l'API backend, qui génère le PDF et l'envoie.
//
// Variables d'environnement (onglet Variables du service Function) :
//   BACKEND_URL = https://<ton-backend>.up.railway.app   (sans slash final)
//   CRON_TOKEN  = <identique à REPORT_CRON_TOKEN du backend>
//   PERIOD      = last_week            (ou "last_month" pour le service mensuel)
//
// Cron Schedule (⚠️ INDISPENSABLE, sinon le service se relance en boucle) :
//   hebdo   → 0 7 * * 1     (lundi 07:00 UTC = 07:00 Conakry)
//   mensuel → 0 7 1 * *     (le 1er à 07:00, avec PERIOD=last_month)
// ─────────────────────────────────────────────────────────────────────────────

// Shim de type : Bun fournit `process` à l'exécution (les types ne sont pas
// installés localement, cette ligne évite juste les avertissements de l'éditeur).
declare const process: { env: Record<string, string | undefined>; exit(code?: number): never };

(async () => {
  const BASE = (process.env.BACKEND_URL || "").replace(/\/+$/, "");
  const TOKEN = process.env.CRON_TOKEN || "";
  const PERIOD = process.env.PERIOD || "last_week";

  if (!BASE || !TOKEN) {
    console.error("❌ BACKEND_URL et CRON_TOKEN sont requis.");
    process.exit(1);
  }

  const url = `${BASE}/api/v1/reports/cron/send?period=${encodeURIComponent(PERIOD)}`;
  console.log(`Appel du rapport (${PERIOD}) → ${url}`);

  const res = await fetch(url, {
    method: "POST",
    headers: { "X-Cron-Token": TOKEN },
  });

  const body = await res.text();
  console.log(`[rapport ${PERIOD}] HTTP ${res.status} → ${body}`);

  process.exit(res.ok ? 0 : 1);
})();
