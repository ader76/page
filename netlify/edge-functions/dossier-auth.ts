import type { Config, Context } from "@netlify/edge-functions";

// Protège le dossier confidentiel par mot de passe (HTTP Basic).
// Le mot de passe est lu dans la variable d'environnement DOSSIER_PASSWORD (jamais dans le dépôt).
// Le nom d'utilisateur est libre ; seul le mot de passe compte.
export default async (request: Request, context: Context) => {
  const expected = Netlify.env.get("DOSSIER_PASSWORD");
  const deny = () =>
    new Response("Accès réservé · Restricted access", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="Dossier confidentiel", charset="UTF-8"',
        "Cache-Control": "no-store",
        "X-Robots-Tag": "noindex, nofollow, noarchive",
      },
    });

  // Échec fermé : sans mot de passe configuré, l'accès est refusé.
  if (!expected) return deny();

  const header = request.headers.get("authorization") || "";
  if (!header.startsWith("Basic ")) return deny();

  let given = "";
  try {
    const decoded = new TextDecoder().decode(
      Uint8Array.from(atob(header.slice(6)), (c) => c.charCodeAt(0)),
    );
    given = decoded.slice(decoded.indexOf(":") + 1);
  } catch {
    return deny();
  }

  // Comparaison à durée constante
  const a = new TextEncoder().encode(given);
  const b = new TextEncoder().encode(expected);
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a[i] ?? 0) ^ (b[i] ?? 0);
  if (diff !== 0) return deny();

  const response = await context.next();
  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("X-Robots-Tag", "noindex, nofollow, noarchive");
  return response;
};

export const config: Config = {
  path: ["/dossier-confidentiel", "/dossier-confidentiel.html"],
  cache: "manual",
};
