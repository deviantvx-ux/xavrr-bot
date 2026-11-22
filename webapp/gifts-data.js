window.XAVRR_GIFTS = {
  "bday_candle": {
    id: "bday_candle",
    name: "B-Day Candle",
    code: "CANDLE",
    rarity: "Common",
    price: 3.0,
    badge: "COMMON",
    accent: "#94a3b8",
    slug: "bday-candle"
  },
  "homemade_cake": {
    id: "homemade_cake",
    name: "Homemade Cake",
    code: "CAKE",
    rarity: "Common",
    price: 3.5,
    badge: "COMMON",
    accent: "#38bdf8",
    slug: "homemade-cake"
  },
  "santa_hat": {
    id: "santa_hat",
    name: "Santa Hat",
    code: "SANTA HAT",
    rarity: "Rare",
    price: 5.5,
    badge: "RARE",
    accent: "#ef4444",
    slug: "santa-hat"
  },
  "victory_medal": {
    id: "victory_medal",
    name: "Victory Medal",
    code: "MEDAL",
    rarity: "Rare",
    price: 15.0,
    badge: "RARE",
    accent: "#f59e0b",
    slug: "victory-medal"
  },
  "artisan_brick": {
    id: "artisan_brick",
    name: "Artisan Brick",
    code: "BRICK",
    rarity: "Epic",
    price: 85.0,
    badge: "EPIC",
    accent: "#f97316",
    slug: "artisan-brick"
  },
  "astral_shard": {
    id: "astral_shard",
    name: "Astral Shard",
    code: "SHARD",
    rarity: "Mythic",
    price: 128.0,
    badge: "MYTHIC",
    accent: "#06b6d4",
    slug: "astral-shard"
  },
  "loot_bag": {
    id: "loot_bag",
    name: "Loot Bag",
    code: "LOOT BAG",
    rarity: "Mythic",
    price: 133.5,
    badge: "MYTHIC",
    accent: "#eab308",
    slug: "loot-bag"
  },
  "precious_peach": {
    id: "precious_peach",
    name: "Precious Peach",
    code: "PEACH",
    rarity: "Mythic",
    price: 247.0,
    badge: "MYTHIC",
    accent: "#fb7185",
    slug: "precious-peach"
  },
  "scared_cat": {
    id: "scared_cat",
    name: "Scared Cat",
    code: "SCARED CAT",
    rarity: "Mythic",
    price: 299.0,
    badge: "MYTHIC",
    accent: "#a855f7",
    slug: "scared-cat"
  },
  "resistance_dog": {
    id: "resistance_dog",
    name: "Resistance Dog",
    code: "RES DOG",
    rarity: "Mythic",
    price: 526.0,
    badge: "MYTHIC",
    accent: "#3b82f6",
    slug: "resistance-dog"
  },
  "durov_cap": {
    id: "durov_cap",
    name: "Durov's Cap",
    code: "DUROV CAP",
    rarity: "Legendary",
    price: 650.0,
    badge: "LEGENDARY",
    accent: "#10b981",
    slug: "durov-cap"
  },
  "heart_locket": {
    id: "heart_locket",
    name: "Heart Locket",
    code: "LOCKET",
    rarity: "Legendary",
    price: 1200.0,
    badge: "LEGENDARY",
    accent: "#ec4899",
    slug: "heart-locket"
  },
  "plush_pepe": {
    id: "plush_pepe",
    name: "Plush Pepe",
    code: "PLUSH PEPE",
    rarity: "Legendary",
    price: 6400.0,
    badge: "LEGENDARY",
    accent: "#22c55e",
    slug: "plush-pepe"
  }
};

window.XAVRR_CASES = [
  {
    id: "daily24",
    badge: "FREE 24H",
    name: "Daily Drop",
    tag: "STARTER GIFT",
    price: 0,
    free: true,
    pool: [
      { giftId: "bday_candle", chance: 50 },
      { giftId: "homemade_cake", chance: 35 },
      { giftId: "santa_hat", chance: 15 }
    ]
  },
  {
    id: "farm_box",
    badge: "FARM",
    name: "Farm Vault",
    tag: "FARM POOL",
    price: 5.0,
    free: false,
    pool: [
      { giftId: "bday_candle", chance: 40 },
      { giftId: "homemade_cake", chance: 38 },
      { giftId: "santa_hat", chance: 22 }
    ]
  },
  {
    id: "lite_gift",
    badge: "LITE",
    name: "Lite Collectibles",
    tag: "LITE GIFT",
    price: 25.0,
    free: false,
    pool: [
      { giftId: "bday_candle", chance: 30 },
      { giftId: "homemade_cake", chance: 30 },
      { giftId: "santa_hat", chance: 25 },
      { giftId: "victory_medal", chance: 15 }
    ]
  },
  {
    id: "dubai_gift",
    badge: "DUBAI",
    name: "Дубай",
    tag: "DUBAI EDITION",
    price: 120.0,
    free: false,
    pool: [
      { giftId: "victory_medal", chance: 35 },
      { giftId: "artisan_brick", chance: 35 },
      { giftId: "astral_shard", chance: 30 }
    ]
  },
  {
    id: "tg_originals",
    badge: "ORIGINALS",
    name: "Telegram Originals",
    tag: "TG GIFT",
    price: 220.0,
    free: false,
    pool: [
      { giftId: "astral_shard", chance: 30 },
      { giftId: "loot_bag", chance: 28 },
      { giftId: "precious_peach", chance: 24 },
      { giftId: "scared_cat", chance: 18 }
    ]
  },
  {
    id: "pepe_club",
    badge: "PEPE CLUB",
    name: "Pepe Syndicate",
    tag: "PEPE GIFT",
    price: 450.0,
    free: false,
    pool: [
      { giftId: "precious_peach", chance: 34 },
      { giftId: "scared_cat", chance: 32 },
      { giftId: "resistance_dog", chance: 22 },
      { giftId: "durov_cap", chance: 12 }
    ]
  },
  {
    id: "king_vault",
    badge: "KING VAULT",
    name: "XAVRR King",
    tag: "HIGH ROLLER",
    price: 950.0,
    free: false,
    pool: [
      { giftId: "resistance_dog", chance: 36 },
      { giftId: "durov_cap", chance: 34 },
      { giftId: "heart_locket", chance: 30 }
    ]
  },
  {
    id: "mythic_crown",
    badge: "MYTHIC VIP",
    name: "Mythic Crown",
    tag: "VIP GIFT",
    price: 2500.0,
    free: false,
    pool: [
      { giftId: "durov_cap", chance: 38 },
      { giftId: "heart_locket", chance: 35 },
      { giftId: "plush_pepe", chance: 27 }
    ]
  }
];
