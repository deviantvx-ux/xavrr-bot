(function () {
  function escapeXml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildSvgDataUrl(gift, size) {
    var w = size || 96;
    var accent = (gift && gift.accent) || "#00d4b6";
    var rarity = (gift && gift.rarity) || "Rare";
    var code = (gift && gift.code) || "NFT";
    var price = gift && gift.price !== undefined ? gift.price : "";

    var ringColor =
      rarity === "Legendary"
        ? "#f5b400"
        : rarity === "Mythic"
        ? "#00d4b6"
        : rarity === "Epic"
        ? "#a855f7"
        : "#64748b";

    var svg =
      "<svg xmlns='http://www.w3.org/2000/svg' width='" +
      w +
      "' height='" +
      w +
      "' viewBox='0 0 96 96'>" +
      "<defs>" +
      "<radialGradient id='bg' cx='35%' cy='25%' r='75%'>" +
      "<stop offset='0%' stop-color='" +
      accent +
      "' stop-opacity='0.42'/>" +
      "<stop offset='65%' stop-color='#111827' stop-opacity='0.96'/>" +
      "<stop offset='100%' stop-color='#07090e' stop-opacity='1'/>" +
      "</radialGradient>" +
      "<linearGradient id='shine' x1='0%' y1='0%' x2='100%' y2='100%'>" +
      "<stop offset='0%' stop-color='#ffffff' stop-opacity='0.35'/>" +
      "<stop offset='50%' stop-color='#ffffff' stop-opacity='0.04'/>" +
      "<stop offset='100%' stop-color='#000000' stop-opacity='0.25'/>" +
      "</linearGradient>" +
      "</defs>" +
      "<rect x='4' y='4' width='88' height='88' rx='22' fill='url(#bg)' stroke='" +
      ringColor +
      "' stroke-width='2.2'/>" +
      "<circle cx='48' cy='42' r='22' fill='" +
      accent +
      "' fill-opacity='0.18' stroke='url(#shine)' stroke-width='1.5'/>" +
      "<polygon points='48,22 64,34 58,55 38,55 32,34' fill='" +
      accent +
      "' fill-opacity='0.35' stroke='#f8fafc' stroke-width='1.4'/>" +
      "<text x='48' y='45' text-anchor='middle' fill='#ffffff' font-family='Inter,system-ui,sans-serif' font-size='10' font-weight='900'>" +
      escapeXml(code.slice(0, 8)) +
      "</text>" +
      "<text x='48' y='77' text-anchor='middle' fill='#e2e8f0' font-family='Inter,system-ui,sans-serif' font-size='9' font-weight='800'>" +
      escapeXml(rarity.toUpperCase()) +
      (price !== "" ? " • " + price : "") +
      "</text>" +
      "</svg>";

    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  function createGiftImg(gift, size, className) {
    var img = document.createElement("img");
    img.src = buildSvgDataUrl(gift, size || 96);
    img.alt = (gift && gift.name) || "Telegram Gift";
    img.className = className || "gift-art-img";
    img.loading = "lazy";
    img.onerror = function () {
      this.onerror = null;
      this.src = buildSvgDataUrl(
        { name: "Gift", code: "GIFT", rarity: "Rare", accent: "#00d4b6", price: "" },
        size || 96
      );
    };
    return img;
  }

  window.XAVRR_GIFT_ART = {
    getUrl: buildSvgDataUrl,
    createImg: createGiftImg
  };
})();
