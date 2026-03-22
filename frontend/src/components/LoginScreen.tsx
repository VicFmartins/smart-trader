import { useState, type FormEvent } from "react";

type LoginScreenProps = {
  loading: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
};

export default function LoginScreen({ loading, onLogin }: LoginScreenProps) {
  const [email, setEmail] = useState("admin@carteira.local");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await onLogin(email, password);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Nao foi possivel iniciar a sessao.");
    } finally {
      setSubmitting(false);
    }
  }

  const busy = loading || submitting;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.12),transparent_30%),linear-gradient(180deg,#07101f_0%,#081320_100%)] px-6 py-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[minmax(0,1.1fr)_460px]">
          <section className="hidden rounded-[36px] border border-white/8 bg-white/[0.03] p-10 text-white shadow-soft lg:block">
            <div className="inline-flex items-center gap-3 rounded-full border border-cyan-300/16 bg-cyan-300/[0.06] px-3 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100">
              <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.7)]" />
              Secure workspace
            </div>
            <h1 className="mt-8 font-display text-5xl font-extrabold tracking-tight text-white">
              Portfolio intelligence com acesso protegido.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-slate-300">
              Entre na plataforma para acessar uploads, fila de revisao, reprocessamento operacional e o dashboard
              executivo com dados vivos da base consolidada.
            </p>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {[
                ["Upload real", "Planilhas e JSON processados via ETL com rastreabilidade."],
                ["Review queue", "Aprovacao humana e reprocessamento com mappings aceitos."],
                ["Executive dashboard", "KPIs, alocacao e posicoes com dados reais da API."]
              ].map(([title, body]) => (
                <div key={title} className="rounded-[24px] border border-white/8 bg-white/[0.04] p-5">
                  <div className="text-sm font-semibold text-white">{title}</div>
                  <div className="mt-3 text-sm leading-7 text-slate-400">{body}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[36px] border border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.06)_0%,rgba(255,255,255,0.03)_100%)] p-8 shadow-soft backdrop-blur">
            <div className="inline-flex items-center gap-3 rounded-full border border-emerald-300/16 bg-emerald-300/[0.08] px-3 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-100">
              Authentication
            </div>
            <h2 className="mt-6 font-display text-3xl font-extrabold tracking-tight text-white">Entrar no workspace</h2>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              Use um usuario ja provisionado para acessar upload, carteira consolidada e fluxo operacional de revisao.
            </p>

            <form className="mt-8 space-y-5" onSubmit={(event) => void handleSubmit(event)}>
              <div>
                <label htmlFor="loginEmail" className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Email
                </label>
                <input
                  id="loginEmail"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="ops@carteiraconsol.local"
                  className="w-full rounded-[20px] border border-white/8 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-300/30 focus:bg-white/[0.05]"
                />
              </div>

              <div>
                <label htmlFor="loginPassword" className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Password
                </label>
                <input
                  id="loginPassword"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Digite sua senha"
                  className="w-full rounded-[20px] border border-white/8 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-300/30 focus:bg-white/[0.05]"
                />
              </div>

              {error ? (
                <div className="rounded-[20px] border border-rose-400/16 bg-rose-400/[0.08] px-4 py-3 text-sm leading-7 text-rose-100">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-[22px] border border-transparent bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 px-4 py-4 text-sm font-semibold text-slate-950 shadow-[0_16px_30px_rgba(56,189,248,0.28)] transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? "Validando acesso..." : "Entrar na plataforma"}
              </button>
            </form>

            <div className="mt-6 rounded-[22px] border border-white/8 bg-white/[0.03] px-4 py-4 text-xs leading-6 text-slate-500">
              Para criar o primeiro admin localmente, rode <code>python scripts/create_admin.py --email seu@email.com</code>.
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
