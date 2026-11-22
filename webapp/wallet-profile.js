(function () {
  var STORAGE_KEY = "xavrr_wallet_profile_v1";

  function getTelegramUser() {
    var tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      return tg.initDataUnsafe.user;
    }
    return null;
  }

  function createDefaultAddress(seed) {
    var chars = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    var out = "UQ";
    var h = Number(seed) || 100001;
    for (var i = 0; i < 38; i++) {
      h = (h * 1103515245 + 12345) & 0x7fffffff;
      out += chars[h % chars.length];
    }
    return out;
  }

  function loadState() {
    var tgUser = getTelegramUser();
    var uid = tgUser && tgUser.id ? tgUser.id : 100001;
    var name =
      tgUser && (tgUser.first_name || tgUser.username)
        ? tgUser.first_name || tgUser.username
        : "XAVRR Player";
    var handle = tgUser && tgUser.username ? "@" + tgUser.username : "@xavrr_user";

    var fallback = {
      userId: uid,
      name: name,
      handle: handle,
      connected: false,
      provider: "GRAM Wallet",
      address: createDefaultAddress(uid),
      stats: {
        casesOpened: 0,
        upgradesDone: 0,
        volumeGram: 0
      }
    };

    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return fallback;
      var parsed = JSON.parse(raw);
      return {
        userId: uid,
        name: name,
        handle: handle,
        connected: Boolean(parsed.connected),
        provider: parsed.provider || "GRAM Wallet",
        address: parsed.address || createDefaultAddress(uid),
        stats: {
          casesOpened: Number(parsed.stats && parsed.stats.casesOpened) || 0,
          upgradesDone: Number(parsed.stats && parsed.stats.upgradesDone) || 0,
          volumeGram: Number(parsed.stats && parsed.stats.volumeGram) || 0
        }
      };
    } catch (e) {
      return fallback;
    }
  }

  var profileState = loadState();

  function saveState() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profileState));
    } catch (e) {}
  }

  function shortAddress(addr) {
    if (!addr || addr.length < 10) return addr || "";
    return addr.slice(0, 6) + "..." + addr.slice(-4);
  }

  function connectWallet(provider) {
    if (provider) {
      profileState.provider = provider;
    }
    profileState.connected = true;
    saveState();
    renderProfileUI();
    return profileState;
  }

  function disconnectWallet() {
    profileState.connected = false;
    saveState();
    renderProfileUI();
    return profileState;
  }

  function recordCaseOpen(spentGram) {
    profileState.stats.casesOpened += 1;
    profileState.stats.volumeGram = Number(
      (profileState.stats.volumeGram + (Number(spentGram) || 0)).toFixed(2)
    );
    saveState();
    renderProfileUI();
  }

  function recordUpgrade(spentGram) {
    profileState.stats.upgradesDone += 1;
    profileState.stats.volumeGram = Number(
      (profileState.stats.volumeGram + (Number(spentGram) || 0)).toFixed(2)
    );
    saveState();
    renderProfileUI();
  }

  function renderProfileUI() {
    var avatarEl = document.getElementById("user-avatar");
    var nameEl = document.getElementById("profile-name");
    var idEl = document.getElementById("profile-id");
    var walletTagEl = document.getElementById("wallet-status");
    var statsEl = document.getElementById("profile-stats");
    var toggleBtn = document.getElementById("toggle-wallet-btn");

    if (avatarEl) {
      avatarEl.textContent = String(profileState.name).charAt(0).toUpperCase() || "X";
    }
    if (nameEl) {
      nameEl.textContent = profileState.name;
    }
    if (idEl) {
      idEl.textContent =
        "ID: " +
        profileState.userId +
        " • " +
        profileState.handle +
        (profileState.connected ? " • " + shortAddress(profileState.address) : " • Disconnected");
    }
    if (walletTagEl) {
      walletTagEl.textContent = profileState.connected
        ? profileState.provider + ": " + shortAddress(profileState.address)
        : "WALLET: NOT CONNECTED";
    }
    if (statsEl) {
      statsEl.textContent =
        "Кейси: " +
        profileState.stats.casesOpened +
        " • Апгрейди: " +
        profileState.stats.upgradesDone +
        " • Оборот: " +
        profileState.stats.volumeGram.toFixed(1) +
        " GRAM";
    }
    if (toggleBtn) {
      toggleBtn.textContent = profileState.connected ? "Відключити гаманець" : "Підключити гаманець";
    }
  }

  window.XAVRR_WALLET_PROFILE = {
    getState: function () {
      return profileState;
    },
    connectWallet: connectWallet,
    disconnectWallet: disconnectWallet,
    recordCaseOpen: recordCaseOpen,
    recordUpgrade: recordUpgrade,
    render: renderProfileUI
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderProfileUI);
  } else {
    renderProfileUI();
  }
})();
