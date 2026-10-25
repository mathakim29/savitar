import { watch } from "fs";
import { join, resolve } from "path";

// env set by savitar (python)
const VENV = resolve(process.env.VIRTUAL_ENV ?? ".venv");
const SRC = resolve(process.env.SAVITAR_SRC ?? "web");

// everything generated lives in the venv
const SV = join(VENV, "node_modules", "svelte");
const OUT = join(VENV, "savitar", "web");
const ENTRY = join(VENV, "savitar", ".entry.js");
const APP = join(SRC, "App.svelte");

const pkg = await Bun.file(join(SV, "package.json")).json();

// resolve "svelte" / "svelte/x" via exports map (browser > default)
const pick = (o) => (typeof o === "string" ? o : o && pick(o.browser ?? o.default));
const sv = (spec) => {
  const hit = pick(pkg.exports["." + spec.slice(6)]);
  return hit ? join(SV, hit) : Bun.resolveSync(spec, VENV);
};

const { compile, compileModule } = await import(sv("svelte/compiler"));

const svelte = {
  name: "svelte",
  setup(b) {
    b.onResolve({ filter: /^svelte(\/|$)/ }, ({ path }) => ({ path: sv(path) }));

    b.onLoad({ filter: /\.svelte$/ }, async ({ path }) => ({
      contents: compile(await Bun.file(path).text(), {
        filename: path,
        generate: "client",
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
    plugins: [svelte],
  });
  if (!r.success) {
    r.logs.forEach((l) => console.error(l));
    if (!process.env.WATCH) process.exit(1);
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
}

await build();

if (process.env.WATCH) {
  let t;
  watch(SRC, { recursive: true }, () => {
    clearTimeout(t);
    t = setTimeout(build, 100);
  });
}
