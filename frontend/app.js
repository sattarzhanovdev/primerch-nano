const state = {
  step: "gender", // gender -> products -> customize -> result
  gender: "female",
  products: [],
  lastError: "",
  selected: null,
  selectedImageUrl: "",
  application: "embroidery",
  placement: "",
  mode: "logo", // logo | text
  logoUrl: "",
  text: "",
  taskId: "",
  taskState: "",
  taskFailMsg: "",
  resultUrl: "",
  jobId: "",
  lastTaskJson: null,
  pollTimer: null,
  tshirtView: "front", // front | back
  sceneMode: "on_model", // on_model | product_only
  externalImageProxyBase: "",
  imageProxyEnabled: true,
  configLoaded: false,
};

const $ = (sel) => document.querySelector(sel);

const SVG_NS = "http://www.w3.org/2000/svg";
const SVG_TAGS = new Set(["svg", "path", "rect", "g", "circle", "ellipse", "line", "polyline", "polygon", "text", "defs", "clipPath", "mask"]);

function el(tag, attrs = {}, children = []) {
  const node = SVG_TAGS.has(tag) ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") {
      if (SVG_TAGS.has(tag)) node.setAttribute("class", v);
      else node.className = v;
    }
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  });
  for (const c of children) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return node;
}

function imgSrc(url) {
  const u = String(url || "");
  if (!u) return "";
  // Same-origin files are fine.
  if (u.startsWith("/")) return u;
  if (u.startsWith(window.location.origin)) return u;
  // Prefer external proxy if configured (for hosts that block outbound requests).
  if (state.externalImageProxyBase) {
    const base = String(state.externalImageProxyBase).replace(/\/+$/, "");
    return `${base}?url=${encodeURIComponent(u)}`;
  }
  // If backend proxy is disabled (e.g. PythonAnywhere outbound restrictions),
  // fall back to direct URLs so images can still render in the browser.
  if (!state.imageProxyEnabled) return u;
  return `/api/image?url=${encodeURIComponent(u)}`;
}

function render() {
  const root = $("#app");
  root.innerHTML = "";

  root.appendChild(renderTopbar());
  if (state.lastError) {
    root.appendChild(el("div", { class: "error-panel" }, [
      el("div", { class: "subtitle" }, ["Что-то пошло не так"]),
      el("div", { class: "help" }, ["Попробуйте ещё раз. Если ошибка повторяется — откройте “Подробнее” и отправьте текст в поддержку."]),
      el("details", {}, [
        el("summary", {}, ["Подробнее"]),
        el("pre", {}, [String(state.lastError)]),
      ]),
      el("div", { class: "hr" }),
      el("button", { class: "btn small", onclick: () => { state.lastError = ""; render(); } }, ["Закрыть"]),
    ]));
  }

  if (state.step === "gender") root.appendChild(renderGender());
  if (state.step === "products") root.appendChild(renderProducts());
  if (state.step === "customize") root.appendChild(renderCustomize());
  if (state.step === "result") root.appendChild(renderResult());
}

function inferProductType(p) {
  const title = String(p?.title || "").toLowerCase();
  const category = String(p?.category || "").toLowerCase();
  const hay = `${title} ${category}`;
  if (hay.includes("кружк") || hay.includes("mug")) return "mug";
  const apparel = ["футболк", "худи", "свитшот", "толстовк", "поло", "рубашк", "дождевик", "плащ", "фартук", "куртк", "жилет", "ветровк"];
  if (apparel.some((m) => hay.includes(m))) return "apparel";
  return "other";
}

function isApparelLike(p) {
  const t = p?.type || inferProductType(p);
  return t === "apparel" || t === "tshirt";
}

function renderTopbar() {
  return el("div", { class: "topbar" }, [
    el("div", {}, [
      el("div", { class: "title" }, ["Визуализация нанесения"]),
      el("div", { class: "subtitle" }, ["Выберите товар, добавьте логотип или текст и получите превью."]),
    ]),
    el("div", { class: "seg" }, [
      el("span", { class: "badge" }, [labelForStep(state.step)]),
      el("button", {
        class: "btn small",
        onclick: () => {
          stopPolling();
          Object.assign(state, {
            step: "gender",
            products: [],
            selected: null,
            selectedImageUrl: "",
            application: "embroidery",
            placement: "",
            mode: "logo",
            logoUrl: "",
            text: "",
            taskId: "",
            taskState: "",
            taskFailMsg: "",
            resultUrl: "",
            jobId: "",
            lastTaskJson: null,
            sceneMode: "on_model",
          });
          render();
        },
      }, ["Начать заново"]),
    ]),
  ]);
}

function labelForStep(step) {
  if (step === "gender") return "Шаг 1: Пол";
  if (step === "products") return "Шаг 2: Товар";
  if (step === "customize") return "Шаг 3: Настройка";
  if (step === "result") return "Шаг 4: Результат";
  return String(step || "");
}

function renderGender() {
  return el("div", { class: "panel" }, [
    el("div", { class: "row" }, [
      el("div", { class: "col" }, [
        el("div", { class: "subtitle" }, ["Выберите пол"]),
        el("div", { class: "hr" }),
        el("div", { class: "seg" }, [
          genderBtn("female", "Женский"),
          genderBtn("male", "Мужской"),
          genderBtn("unisex", "Унисекс"),
          genderBtn("all", "Все"),
        ]),
        el("div", { class: "hr" }),
        el("button", {
          class: "btn primary",
          onclick: async () => {
            await loadProducts();
            state.step = "products";
            render();
          },
        }, ["Далее"]),
        el("div", { class: "help" }, ["Пол используется для рекомендаций и сцены “на модели”."]),
      ]),
      el("div", { class: "col" }, [
        el("div", { class: "subtitle" }, ["Как это работает"]),
        el("div", { class: "hr" }),
        el("div", { class: "help" }, ["Выберите товар → зону нанесения → добавьте логотип или текст → получите изображение с нанесением."]),
      ]),
    ]),
  ]);
}

function genderBtn(value, label) {
  const active = state.gender === value;
  return el("button", {
    class: `btn ${active ? "success" : ""}`,
    onclick: () => {
      state.gender = value;
      render();
    },
  }, [label]);
}

async function loadProducts() {
  state.lastError = "";
  const url = new URL("/api/products", window.location.origin);
  url.searchParams.set("gender", state.gender);
  url.searchParams.set("limit", "60");

  const res = await fetch(url.toString());
  const text = await res.text();
  if (!res.ok) {
    state.products = [];
    state.lastError = `GET /api/products -> ${res.status} ${text}`;
    return;
  }
  const data = JSON.parse(text);
  state.products = data.items || [];
}

function renderProducts() {
  const search = el("input", {
    class: "input",
    placeholder: "Поиск (название/категория/артикул)",
    value: "",
    oninput: async (e) => {
      state.lastError = "";
      const q = e.target.value || "";
      const url = new URL("/api/products", window.location.origin);
      url.searchParams.set("gender", state.gender);
      url.searchParams.set("q", q);
      url.searchParams.set("limit", "60");
      const res = await fetch(url.toString());
      const text = await res.text();
      if (!res.ok) {
        state.products = [];
        state.lastError = `GET /api/products?q=... -> ${res.status} ${text}`;
        render();
        return;
      }
      const data = JSON.parse(text);
      state.products = data.items || [];
      render();
    },
  });

  const grid = el("div", { class: "grid" }, state.products.map((p) => productCard(p)));

  return el("div", { class: "panel" }, [
    el("div", { class: "row" }, [
      el("div", { class: "col" }, [
        el("div", { class: "subtitle" }, ["Выберите товар"]),
        el("div", { class: "hr" }),
        search,
      ]),
      el("div", { class: "col" }, [
        el("div", { class: "seg" }, [
          el("button", {
            class: "btn small",
            onclick: () => {
              state.step = "gender";
              render();
            },
          }, ["← Назад"]),
          el("span", { class: "badge" }, [`Товаров: ${state.products.length}`]),
        ]),
      ]),
    ]),
    el("div", { class: "hr" }),
    grid,
  ]);
}

function productCard(p) {
  const img = (p.images && p.images[0]) || "";
  const pType = p.type || inferProductType(p);
  return el("div", {
    class: "card",
    onclick: () => {
      stopPolling();
      state.selected = p;
      state.step = "customize";
      state.selectedImageUrl = (p.images && p.images[0]) || "";
      state.application = "embroidery";
      state.placement = "";
      state.tshirtView = "front";
      state.mode = "logo";
      state.logoUrl = "";
      state.text = "";
      state.taskId = "";
      state.taskState = "";
      state.taskFailMsg = "";
      state.resultUrl = "";
      state.jobId = "";
      state.lastTaskJson = null;
      state.lastError = "";
      state.sceneMode = "on_model";
      render();
    },
  }, [
    el("img", { src: imgSrc(img), alt: p.title || "product" }),
    el("div", { class: "p" }, [
      el("div", { class: "h" }, [p.title || "—"]),
      el("div", { class: "m" }, [`${p.category || ""} • ${p.price || ""} • арт. ${p.article || ""}`]),
      el("div", { class: "m" }, [`тип: ${pType} • пол: ${p.gender}`]),
    ]),
  ]);
}

function renderCustomize() {
  const p = state.selected;
  if (!p) return el("div", { class: "panel" }, ["Нет товара"]);
  const isApparel = isApparelLike(p);

  const left = el("div", { class: "panel" }, [
    el("div", { class: "subtitle" }, ["Настройте нанесение"]),
    el("div", { class: "hr" }),
    el("div", { class: "row" }, [
      el("div", { class: "col settings-col" }, [
        el("div", { class: "subtitle" }, ["Фото товара (выбери)"]),
        el("div", { class: "hr" }),
        productPhotosPicker(p),
        el("div", { class: "hr" }),
        el("label", { class: "subtitle" }, ["Сцена"]),
        sceneModeSwitch(),
        el("div", { class: "hr" }),
        el("label", { class: "subtitle" }, ["Вид нанесения"]),
        applicationSelect(),
        el("div", { class: "hr" }),
        el("label", { class: "subtitle" }, ["Дизайн"]),
        modeSwitch(),
        el("div", { class: "hr" }),
        state.mode === "logo" ? logoUploader() : textInput(),
        el("div", { class: "hr" }),
        el("button", {
          class: `btn primary`,
          onclick: () => onGenerate(),
        }, ["Создать визуализацию"]),
      ]),
      el("div", { class: "col zones-col", id: "zones-anchor" }, [
        el("div", { class: "subtitle" }, ["Выберите зону нанесения"]),
        el("div", { class: "hr" }),
        isApparel
          ? el("div", { class: "seg" }, [
              el("button", {
                class: `btn small ${state.tshirtView === "front" ? "success" : ""}`,
                onclick: () => { state.tshirtView = "front"; render(); },
              }, ["Перед"]),
              el("button", {
                class: `btn small ${state.tshirtView === "back" ? "success" : ""}`,
                onclick: () => { state.tshirtView = "back"; render(); },
              }, ["Спина"]),
            ])
          : el("div", { style: "height: 0px;" }),
        el("div", { class: "hr" }),
        el("div", { class: "mock" }, [
          isApparel ? apparelZonePicker() : (p.type || inferProductType(p)) === "mug" ? mugZones() : genericZones(),
        ]),
        el("div", { class: "help" }, [
          state.placement ? "Зона выбрана" : "Выберите зону, чтобы продолжить.",
        ]),
      ]),
    ]),
  ]);

  const right = el("div", { class: "panel" }, [
    el("div", { class: "subtitle" }, ["Выбранный товар"]),
    el("div", { class: "hr" }),
    el("img", {
      src: imgSrc(state.selectedImageUrl || (p.images && p.images[0]) || ""),
      style: "width:100%;border-radius:14px;border:1px solid rgba(255,255,255,0.10);",
      alt: p.title || "product",
    }),
    el("div", { class: "hr" }),
    el("div", { class: "help" }, [
      el("div", { html: `<div><b>${escapeHtml(p.title || "")}</b></div>` }),
      p.price ? el("div", { html: `<div>${escapeHtml(p.price || "")}</div>` }) : el("div", { style: "height: 0px;" }),
    ]),
    el("div", { class: "hr" }),
    el("button", { class: "btn small", onclick: () => { state.step = "products"; render(); } }, ["← К товарам"]),
  ]);

  return el("div", { class: "layout" }, [left, right]);
}

function apparelZonePicker() {
  const sleeveLeft = el("div", { class: "zone-card" }, [
    sleeveSvg("wearer_left_sleeve"),
    el("div", { class: "zone-caption" }, ["Левый рукав"]),
  ]);

  const center = el("div", { class: "zone-card center" }, [
    torsoSvg(state.tshirtView === "back" ? "back" : "front"),
    el("div", { class: "zone-caption" }, [state.tshirtView === "back" ? "Спина" : "Перед"]),
  ]);

  const sleeveRight = el("div", { class: "zone-card" }, [
    sleeveSvg("wearer_right_sleeve"),
    el("div", { class: "zone-caption" }, ["Правый рукав"]),
  ]);

  return el("div", { class: "zone-picker" }, [sleeveLeft, center, sleeveRight]);
}

function sleeveSvg(placementId) {
  const svg = el("svg", { class: "zone-svg", viewBox: "0 0 220 160", preserveAspectRatio: "xMidYMid meet" });
  // Sleeve outline (simple trapezoid)
  svg.appendChild(el("path", {
    d: "M30 30 C55 15, 165 15, 190 30 L205 120 C207 132, 198 142, 186 142 H34 C22 142, 13 132, 15 120 L30 30 Z",
    fill: "rgba(255,255,255,0.03)",
    stroke: "rgba(255,255,255,0.16)",
    "stroke-width": "2",
  }));

  const g = el("g", { class: "zones" });
  g.appendChild(el("rect", {
    class: `zone ${state.placement === placementId ? "selected" : ""}`,
    // upper sleeve near shoulder
    x: 56, y: 42, width: 108, height: 58, rx: "10",
    title: placementId,
    onclick: () => { state.placement = placementId; render(); },
  }));
  svg.appendChild(g);
  return svg;
}

function torsoSvg(mode) {
  const svg = el("svg", { class: "zone-svg", viewBox: "0 0 260 200", preserveAspectRatio: "xMidYMid meet" });
  // T-shirt/sweatshirt simplified outline
  svg.appendChild(el("path", {
    d: "M78 20c12-10 26-15 52-15s40 5 52 15l22 18c8 7 10 18 6 28l-10 28c-2 6-8 9-14 8l-14-4v76c0 12-10 22-22 22H90c-12 0-22-10-22-22V98l-14 4c-6 1-12-2-14-8L30 66c-4-10-2-21 6-28l42-18z",
    fill: "rgba(255,255,255,0.03)",
    stroke: "rgba(255,255,255,0.16)",
    "stroke-width": "2",
  }));

  const g = el("g", { class: "zones" });
  if (mode === "back") {
    g.appendChild(el("rect", {
      class: `zone ${state.placement === "back" ? "selected" : ""}`,
      x: 84, y: 56, width: 92, height: 108, rx: "10",
      title: "back",
      onclick: () => { state.placement = "back"; render(); },
    }));
  } else {
    g.appendChild(el("rect", {
      class: `zone ${state.placement === "chest" ? "selected" : ""}`,
      x: 92, y: 56, width: 76, height: 38, rx: "10",
      title: "chest",
      onclick: () => { state.placement = "chest"; render(); },
    }));
    g.appendChild(el("rect", {
      class: `zone ${state.placement === "front" ? "selected" : ""}`,
      x: 84, y: 98, width: 92, height: 66, rx: "10",
      title: "front",
      onclick: () => { state.placement = "front"; render(); },
    }));
    g.appendChild(el("rect", {
      class: `zone ${state.placement === "belly" ? "selected" : ""}`,
      x: 92, y: 136, width: 76, height: 28, rx: "10",
      title: "belly",
      onclick: () => { state.placement = "belly"; render(); },
    }));
  }
  svg.appendChild(g);
  return svg;
}

function productPhotosPicker(p) {
  const imgs = Array.isArray(p.images) ? p.images : [];
  const grid = el("div", { class: "thumbs" }, []);

  // Upload custom product photo (works even if external images are blocked).
  const uploadWrap = el("div", {}, []);
  const uploadInput = el("input", {
    class: "input",
    type: "file",
    accept: "image/*",
    onchange: async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch("/api/uploads", { method: "POST", body: form });
        const text = await res.text();
        if (!res.ok) throw new Error(`Upload failed: ${res.status} ${text}`);
        const data = JSON.parse(text);
        state.selectedImageUrl = data.url;
        render();
      } catch (err) {
        state.lastError = String(err);
        render();
      }
    },
  });
  uploadWrap.appendChild(uploadInput);
  grid.appendChild(el("div", { class: "panel", style: "padding:10px;border-radius:12px;display:grid;gap:8px;" }, [
    el("div", { class: "subtitle" }, ["Загрузить фото"]),
    uploadWrap,
  ]));

  if (!imgs.length) {
    return el("div", {}, [
      grid,
      el("div", { class: "help" }, ["Фото из каталога недоступны — загрузите своё фото товара."]),
    ]);
  }

  for (const url of imgs.slice(0, 24)) {
    grid.appendChild(el("img", {
      class: `thumb ${state.selectedImageUrl === url ? "selected" : ""}`,
      src: imgSrc(url),
      alt: "photo",
      onclick: () => {
        state.selectedImageUrl = url;
        render();
      },
    }));
  }
  return grid;
}

function applicationSelect() {
  const sel = el("select", {
    onchange: (e) => {
      state.application = e.target.value;
    },
  }, [
    opt("print", "Принт (print)"),
    opt("embroidery", "Вышивка (embroidery)"),
    opt("screen_print", "Шелкография (screen_print)"),
    opt("dtf", "DTF (dtf)"),
    opt("dtg", "DTG (dtg)"),
    opt("heat_transfer", "Термотрансфер (heat_transfer)"),
    opt("patch", "Нашивка (patch)"),
    opt("engraving", "Гравировка (engraving)"),
    opt("sublimation", "Сублимация (sublimation)"),
    opt("flex", "Флекс (flex)"),
    opt("flock", "Флок (flock)"),
    opt("puff_print", "Пухлый принт (puff_print)"),
    opt("high_density", "Высокая плотность (high_density)"),
    opt("reflective", "Светоотражающий (reflective)"),
    opt("foil", "Фольга (foil)"),
    opt("glitter", "Глиттер (glitter)"),
    opt("neon", "Неон (neon)"),
    opt("glow", "Свечение (glow)"),
    opt("rubber_print", "Резиновый принт (rubber_print)"),
    opt("water_based", "Водная краска (water_based)"),
    opt("plastisol", "Пластизоль (plastisol)"),
  ]);
  sel.value = state.application;
  return sel;
}

function opt(value, label) {
  return el("option", { value }, [label]);
}

function modeSwitch() {
  return el("div", { class: "seg" }, [
    el("button", {
      class: `btn ${state.mode === "logo" ? "success" : ""}`,
      onclick: () => {
        state.mode = "logo";
        render();
      },
    }, ["Логотип"]),
    el("button", {
      class: `btn ${state.mode === "text" ? "success" : ""}`,
      onclick: () => {
        state.mode = "text";
        render();
      },
    }, ["Текст"]),
  ]);
}

function logoUploader() {
  const wrap = el("div", {}, []);
  const info = el("div", { class: "help" }, [
    state.logoUrl ? "Логотип загружен" : "Загрузите файл логотипа (PNG/JPG/WebP).",
  ]);
  const warn = el("div", { class: "help", style: "color: rgba(255, 200, 120, 0.95)" }, []);
  const input = el("input", {
    class: "input",
    type: "file",
    accept: "image/*",
    onchange: async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      state.logoUrl = "";
      info.textContent = "Загрузка...";
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch("/api/uploads", { method: "POST", body: form });
        const text = await res.text();
        if (!res.ok) throw new Error(`Upload failed: ${res.status} ${text}`);
        const data = JSON.parse(text);
        state.logoUrl = data.url;
        info.textContent = `Загружено: ${state.logoUrl}`;
        warn.textContent = "";
      } catch (err) {
        info.textContent = `Ошибка: ${err}`;
      }
    },
  });
  wrap.appendChild(input);
  wrap.appendChild(info);
  wrap.appendChild(warn);
  return wrap;
}

function textInput() {
  return el("div", {}, [
    el("input", {
      class: "input",
      placeholder: "Текст для нанесения (backend сделает PNG)",
      value: state.text,
      oninput: (e) => {
        state.text = e.target.value;
      },
    }),
    el("div", { class: "help" }, ["Введите слово или короткую фразу."]),
  ]);
}

function tshirtZones() {
  const zonesFront = [
    { id: "wearer_right_sleeve", label: "Правый рукав", x: 260, y: 150, w: 90, h: 75 },
    { id: "wearer_left_sleeve", label: "Левый рукав", x: 50, y: 150, w: 90, h: 75 },
    { id: "chest", label: "Грудь", x: 130, y: 185, w: 140, h: 110 },
    { id: "belly", label: "Живот", x: 130, y: 305, w: 140, h: 120 },
  ];
  const zonesBack = [
    { id: "back", label: "Спина", x: 120, y: 175, w: 160, h: 240 },
    { id: "wearer_right_sleeve", label: "Правый рукав", x: 260, y: 150, w: 90, h: 75 },
    { id: "wearer_left_sleeve", label: "Левый рукав", x: 50, y: 150, w: 90, h: 75 },
  ];
  const zones = state.tshirtView === "back" ? zonesBack : zonesFront;

  const svg = el("svg", { width: "360", height: "480", viewBox: "0 0 360 480" });
  svg.appendChild(el("path", {
    d: "M120 60c20-18 40-28 60-28s40 10 60 28l40 40c18 18 22 42 14 64l-18 48c-4 10-14 16-24 14l-26-6v210c0 22-18 40-40 40H140c-22 0-40-18-40-40V220l-26 6c-10 2-20-4-24-14l-18-48c-8-22-4-46 14-64l40-40z",
    fill: "rgba(255,255,255,0.06)",
    stroke: "rgba(255,255,255,0.18)",
    "stroke-width": "2",
  }));

  const g = el("g", { class: "zones" });
  for (const z of zones) {
    const rect = el("rect", {
      class: `zone ${state.placement === z.id ? "selected" : ""}`,
      x: z.x, y: z.y, width: z.w, height: z.h, rx: "10",
      title: z.label,
      onclick: () => { state.placement = z.id; render(); },
    });
    g.appendChild(rect);
  }
  svg.appendChild(g);
  return svg;
}

function mugZones() {
  const zones = [
    { id: "mug_left", label: "Слева", x: 80, y: 150, w: 90, h: 110 },
    { id: "mug_wrap", label: "По кругу", x: 95, y: 125, w: 170, h: 160 },
    { id: "mug_right", label: "Справа", x: 190, y: 150, w: 90, h: 110 },
  ];

  const svg = el("svg", { width: "360", height: "420", viewBox: "0 0 360 420" });
  svg.appendChild(el("path", {
    d: "M110 90h140c12 0 22 10 22 22v200c0 26-22 48-48 48H136c-26 0-48-22-48-48V112c0-12 10-22 22-22z",
    fill: "rgba(255,255,255,0.06)",
    stroke: "rgba(255,255,255,0.18)",
    "stroke-width": "2",
  }));
  svg.appendChild(el("path", {
    d: "M272 150h24c26 0 46 20 46 46s-20 46-46 46h-24v-24h18c14 0 22-10 22-22s-8-22-22-22h-18v-24z",
    fill: "rgba(255,255,255,0.03)",
    stroke: "rgba(255,255,255,0.14)",
    "stroke-width": "2",
  }));

  const g = el("g", { class: "zones" });
  for (const z of zones) {
    g.appendChild(el("rect", {
      class: `zone ${state.placement === z.id ? "selected" : ""}`,
      x: z.x, y: z.y, width: z.w, height: z.h, rx: "12",
      title: z.label,
      onclick: () => { state.placement = z.id; render(); },
    }));
  }
  svg.appendChild(g);
  return svg;
}

function genericZones() {
  const zones = [
    { id: "front", label: "Front", x: 96, y: 96, w: 168, h: 140 },
    { id: "back", label: "Back", x: 96, y: 246, w: 168, h: 74 },
    { id: "left_side", label: "Left side", x: 58, y: 130, w: 30, h: 150 },
    { id: "right_side", label: "Right side", x: 272, y: 130, w: 30, h: 150 },
    { id: "top", label: "Top", x: 110, y: 58, w: 140, h: 28 },
    { id: "bottom", label: "Bottom", x: 110, y: 328, w: 140, h: 24 },
  ];
  const svg = el("svg", { width: "360", height: "360", viewBox: "0 0 360 360" });
  svg.appendChild(el("rect", {
    x: 60, y: 40, width: 240, height: 280, rx: "22",
    fill: "rgba(255,255,255,0.06)",
    stroke: "rgba(255,255,255,0.18)",
    "stroke-width": "2",
  }));
  const g = el("g", { class: "zones" });
  for (const z of zones) {
    g.appendChild(el("rect", {
      class: `zone ${state.placement === z.id ? "selected" : ""}`,
      x: z.x, y: z.y, width: z.w, height: z.h, rx: "14",
      title: z.label,
      onclick: () => { state.placement = z.id; render(); },
    }));
  }
  svg.appendChild(g);
  return svg;
}

function sceneModeSwitch() {
  return el("div", { class: "seg" }, [
    el("button", {
      class: `btn ${state.sceneMode === "on_model" ? "success" : ""}`,
      onclick: () => { state.sceneMode = "on_model"; render(); },
    }, ["На модели"]),
    el("button", {
      class: `btn ${state.sceneMode === "product_only" ? "success" : ""}`,
      onclick: () => { state.sceneMode = "product_only"; render(); },
    }, ["Только товар"]),
  ]);
}

async function onGenerate() {
  if (!state.selected) return;
  state.lastError = "";
  if (!state.placement) {
    alert("Выбери зону нанесения");
    return;
  }
  if (state.mode === "logo" && !state.logoUrl) {
    alert("Загрузи логотип");
    return;
  }
  if (state.mode === "text" && !state.text.trim()) {
    alert("Введи текст");
    return;
  }

  stopPolling();
  state.taskId = "";
  state.taskState = "";
  state.taskFailMsg = "";
  state.resultUrl = "";
  state.jobId = "";
  state.lastTaskJson = null;
  state.step = "result";
  render();

  const body = {
    productId: String(state.selected.id || state.selected.url || state.selected.article),
    productArticle: String(state.selected.article || ""),
    productImageUrl: state.selectedImageUrl || "",
    placement: state.placement,
    application: state.application,
    scene_mode: state.sceneMode,
    model_gender: state.gender === "male" ? "male" : state.gender === "female" ? "female" : "neutral",
    numImages: 1,
    image_size: "4:3",
  };
  if (state.mode === "logo") body.logoUrl = state.logoUrl;
  if (state.mode === "text") body.text = state.text;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    if (!res.ok) {
      state.lastError = `POST /api/generate -> ${res.status} ${text}`;
      state.lastTaskJson = { error: state.lastError };
      render();
      return;
    }
    const data = JSON.parse(text);
    state.lastTaskJson = data;

    state.jobId = data?.jobId || "";
    const taskId = data?.kieTaskId || data?.response?.data?.taskId || data?.response?.data?.task_id || data?.response?.data?.id;
    state.taskId = taskId || "";

    render();

    if (state.jobId) startJobPolling(state.jobId);
    else if (state.taskId) startPolling(state.taskId);
  } catch (err) {
    state.lastTaskJson = { error: String(err) };
    state.lastError = String(err);
    render();
  }
}

function renderResult() {
  const task = state.taskId
    ? el("span", { class: "badge" }, [`Номер: ${state.taskId.slice(0, 8)}`])
    : state.jobId
      ? el("span", { class: "badge" }, [`Заявка: ${state.jobId.slice(0, 8)}`])
      : el("span", { class: "badge" }, ["Номер: —"]);
  const statusBadge = state.taskState ? el("span", { class: "badge" }, [state.taskState]) : el("span", { class: "badge" }, ["в процессе"]);

  const resultNode = (() => {
    if (state.resultUrl) {
      return el("div", {}, [
        el("img", {
          src: imgSrc(state.resultUrl),
          alt: "result",
          style: "width:100%;border-radius:14px;border:1px solid rgba(255,255,255,0.10);",
        }),
      ]);
    }
    if (state.taskState === "failed" || state.taskState === "error" || state.taskState === "fail") {
      return el("div", { class: "help" }, [`Ошибка генерации: ${state.taskFailMsg || "unknown"}`]);
    }
    return el("div", { class: "help" }, ["Ждем генерацию… (polling каждые 3 сек)"]);
  })();

  const imgBox = el("div", { class: "panel" }, [
    el("div", { class: "subtitle" }, ["Результат"]),
    el("div", { class: "hr" }),
    el("div", { class: "seg" }, [
      el("button", { class: "btn small", onclick: () => { state.step = "customize"; render(); } }, ["← Назад"]),
      task,
      statusBadge,
      el("button", {
        class: "btn small",
        onclick: async () => {
          if (state.jobId) return await pollJobOnce(state.jobId);
          if (state.taskId) return await pollOnce(state.taskId);
        },
      }, ["Обновить"]),
      el("button", { class: "btn small danger", onclick: () => stopPolling() }, ["Стоп polling"]),
    ]),
    el("div", { class: "hr" }),
    el("div", { id: "resultImage" }, [resultNode]),
  ]);

  return el("div", { class: "layout" }, [imgBox, el("div", { class: "panel" }, [
    el("div", { class: "subtitle" }, ["Действия"]),
    el("div", { class: "hr" }),
    el("button", {
      class: "btn primary",
      onclick: () => {
        stopPolling();
        state.step = "products";
        render();
      },
    }, ["Сделать ещё"]),
    el("div", { class: "help" }, ["Можно выбрать другой товар или другую зону нанесения."]),
  ])]);
}

function startPolling(taskId) {
  pollOnce(taskId);
  state.pollTimer = setInterval(() => pollOnce(taskId), 3000);
}

function stopPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
}

async function pollOnce(taskId) {
  try {
    const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`);
    const text = await res.text();
    if (!res.ok) {
      state.lastError = `GET /api/tasks/{taskId} -> ${res.status} ${text}`;
      render();
      return;
    }
    const data = JSON.parse(text);
    state.lastTaskJson = data;
    const record = data?.recordInfo?.data || {};
    const successFlag = record?.successFlag;
    if (successFlag === 1) state.taskState = "success";
    else if (successFlag === 2 || successFlag === 3) state.taskState = "failed";
    else state.taskState = record?.state || record?.status || "generating";
    state.taskFailMsg = record?.errorMessage || record?.failMsg || record?.failMessage || "";
    const urls = data?.result?.resultUrls || data?.result?.result_urls || [];
    state.resultUrl = Array.isArray(urls) && urls.length ? urls[0] : "";
    render();
  } catch (err) {
    state.lastTaskJson = { error: String(err) };
    state.lastError = String(err);
    render();
  }
}

function startJobPolling(jobId) {
  pollJobOnce(jobId);
  state.pollTimer = setInterval(() => pollJobOnce(jobId), 3000);
}

async function pollJobOnce(jobId) {
  try {
    const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
    const text = await res.text();
    if (!res.ok) {
      state.lastError = `GET /api/jobs/{jobId} -> ${res.status} ${text}`;
      render();
      return;
    }
    const data = JSON.parse(text);
    state.lastTaskJson = data;
    state.taskId = data?.kieTaskId || state.taskId;
    state.taskState = data?.state || "в процессе";
    if (state.taskId && data?.task) {
      const record = data.task?.recordInfo?.data || {};
      const successFlag = record?.successFlag;
      if (successFlag === 1) state.taskState = "success";
      else if (successFlag === 2 || successFlag === 3) state.taskState = "failed";
      else state.taskState = record?.state || state.taskState;
      const urls = data.task?.result?.resultUrls || [];
      state.resultUrl = Array.isArray(urls) && urls.length ? urls[0] : "";
      state.taskFailMsg = record?.errorMessage || record?.failMsg || "";
    }
    render();
  } catch (err) {
    state.lastError = String(err);
    render();
  }
}

function escapeHtml(s) {
  return String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
function escapeAttr(s) {
  return String(s).replaceAll('"', "&quot;");
}

async function loadPublicConfig() {
  if (state.configLoaded) return;
  try {
    const res = await fetch("/api/public-config");
    const text = await res.text();
    if (res.ok) {
      const cfg = JSON.parse(text);
      state.externalImageProxyBase = String(cfg?.externalImageProxyBase || "").trim();
      state.imageProxyEnabled = Boolean(cfg?.imageProxyEnabled);
    }
  } catch {
    // ignore
  } finally {
    state.configLoaded = true;
  }
}

async function init() {
  await loadPublicConfig();
  render();
}

init();
