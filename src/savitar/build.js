import { watch, readFileSync, existsSync } from "fs";
import { dirname, join, resolve } from "path";


// env set by savitar (python)
const VENV = resolve(process.env.VIRTUAL_ENV ?? ".venv");
const SRC = resolve(process.env.SAVITAR_SRC ?? "web");
const OUT = resolve(process.env.SAVITAR_OUT ?? join(VENV, "savitar", "web"));
const WATCH = !!process.env.WATCH;

// everything generated lives in the venv
const ENTRY = join(dirname(OUT), ".entry.js");
const READY = join(dirname(OUT), ".ready"); // written after every build attempt
const APP = join(SRC, "App.svelte");
const NM = join(VENV, "node_modules");

// ---- resolve packages from <venv>/node_modules (browser > import > module > default)
const COND = ["browser", "import", "module", "default"];
const pick = (o) => {
  if (typeof o === "string") return o;
  if (Array.isArray(o)) {
    for (const x of o) {
      const r = pick(x);
      if (r) return r;
    }
    return;
  }
  if (o && typeof o === "object")
    for (const k of COND)
      if (k in o) {
        const r = pick(o[k]);
        if (r) return r;
      }
};

function fromExports(exp, sub) {
  const isMap =
    exp && typeof exp === "object" && !Array.isArray(exp) &&
    Object.keys(exp).some((k) => k.startsWith("."));
  if (!isMap) return sub === "." ? pick(exp) : undefined;
  if (exp[sub] !== undefined) return pick(exp[sub]);
  for (const k of Object.keys(exp)) {
    const i = k.indexOf("*");
    if (i < 0) continue;
    const pre = k.slice(0, i);
    const suf = k.slice(i + 1);
    if (sub.startsWith(pre) && sub.endsWith(suf) && sub.length >= k.length - 1) {
      const t = pick(exp[k]);
      if (t) return t.replace("*", sub.slice(pre.length, sub.length - suf.length));
    }
  }
}

const tryResolve = (spec, dir) => {
  try {
    return Bun.resolveSync(spec, dir);
  } catch {
    return undefined;
  }
};

const hasLocal = (name, dir) => {
  for (let d = dir; ; d = dirname(d)) {
    if (existsSync(join(d, "node_modules", name, "package.json"))) return true;
    if (dirname(d) === d) return false;
  }
};

function resolveVenv(spec) {
  const parts = spec.split("/");
  const name = spec.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
  const sub = "." + spec.slice(name.length); // "." or "./x"
  const dir = join(NM, name);
  let pj;
  try {
    pj = JSON.parse(readFileSync(join(dir, "package.json"), "utf8"));
  } catch {
    return undefined;
  }
  let t;
  if (pj.exports !== undefined) {
    t = fromExports(pj.exports, sub);
  } else if (sub === ".") {
    t = (typeof pj.browser === "string" && pj.browser) || pj.module || pj.main || "index.js";
  } else {
    t = sub.slice(2);
  }
  if (!t) return undefined;
  t = t.replace(/^\.\//, "");
  const f = join(dir, t);
  return existsSync(f) ? f : (tryResolve("./" + t, dir) ?? f);
}

// ---- svelte compiler (always from the venv)
const compilerPath = resolveVenv("svelte/compiler");
if (!compilerPath) {
  console.error(`[savitar] svelte not found in ${NM}`);
  process.exit(1);
}
const { compile, compileModule } = await import(compilerPath);

const svelte = {
  name: "svelte",
  setup(b) {
    b.onResolve({ filter: /^svelte(\/|$)/ }, ({ path }) => {
      const p = resolveVenv(path) ?? tryResolve(path, VENV);
      return p ? { path: p } : undefined;
    });

    // Other bare imports: project-local node_modules wins (default resolution),
    // otherwise fall back to packages installed in the venv (`savitar pkg add`).
    b.onResolve({ filter: /^[^./][^:]*$/ }, ({ path, importer }) => {
  const parts = path.split("/");
  const name = path.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
  if (hasLocal(name, importer ? dirname(importer) : SRC)) return undefined;
  const p = resolveVenv(path);
  return p ? { path: p } : undefined;
});

    b.onLoad({ filter: /\.svelte$/ }, async ({ path }) => ({
      contents: compile(await Bun.file(path).text(), {
        filename: path,
        generate: "client",
        css: "injected", // keep <style> blocks (Svelte 5 default drops them into a separate file)
      }).js.code,
      loader: "js",
    }));

    b.onLoad({ filter: /\.svelte\.(js|ts)$/ }, async ({ path }) => {
      let src = await Bun.file(path).text();
      if (path.endsWith(".ts"))
        src = new Bun.Transpiler({ loader: "ts" }).transformSync(src);
      return {
        contents: compileModule(src, { filename: path, generate: "client" }).js.code,
        loader: "js",
      };
    });
  },
};

async function build() {
  try {
    await Bun.write(
      ENTRY,
      `import { mount } from "svelte";
import App from ${JSON.stringify(APP)};
mount(App, { target: document.getElementById("app") });
`
    );
    const r = await Bun.build({
      entrypoints: [ENTRY],
      outdir: OUT,
      naming: "main.js",
      target: "browser",
      minify: !WATCH,
      plugins: [svelte],
    });
    if (!r.success) {
      r.logs.forEach((l) => console.error(l));
      if (!WATCH) process.exit(1);
      return;
    }

    await Bun.write(
      join(OUT, "index.html"),
      `<!DOCTYPE html>
<html>
  <head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>App</title></head>
  <body>
    <div id="app"></div>
    <script type="module" src="/main.js"></script>
  </body>
</html>`
    );
    console.log("[savitar] built", new Date().toLocaleTimeString());
  } catch (e) {
    console.error(e);
    if (!WATCH) process.exit(1);
  } finally {
    await Bun.write(READY, String(Date.now()));
  }
}

await build();

if (WATCH) {
  let t;
  watch(SRC, { recursive: true }, () => {
    clearTimeout(t);
    t = setTimeout(build, 100);
  });
}
