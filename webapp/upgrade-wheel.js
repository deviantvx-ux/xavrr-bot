(function () {
  function getCatalog() {
    var gifts = window.XAVRR_GIFTS || {};
    return Object.keys(gifts)
      .map(function (key) {
        return gifts[key];
      })
      .sort(function (a, b) {
        return Number(a.price) - Number(b.price);
      });
  }

  function calcChancePercent(sourcePrice, targetPrice) {
    var src = Number(sourcePrice) || 0;
    var dst = Number(targetPrice) || 0;
    if (src <= 0 || dst <= 0) return 5;
    var raw = (src / dst) * 80;
    var clamped = Math.max(5, Math.min(85, raw));
    return Number(clamped.toFixed(1));
  }

  function makeSerial() {
    return "#" + Math.floor(10 + Math.random() * 4990);
  }

  function drawWheel(canvasEl, chancePercent, angleDeg) {
    if (!canvasEl) return;
    var ctx = canvasEl.getContext("2d");
    if (!ctx) return;

    var size = canvasEl.width;
    var cx = size / 2;
    var cy = size / 2;
    var r = size / 2 - 8;
    var chance = Math.max(5, Math.min(85, Number(chancePercent) || 5));
    var winRad = (chance / 100) * Math.PI * 2;
    var rotRad = ((Number(angleDeg) || 0) * Math.PI) / 180;

    ctx.clearRect(0, 0, size, size);

    // Зелений сектор шансу успіху
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, rotRad - Math.PI / 2, rotRad - Math.PI / 2 + winRad);
    ctx.closePath();
    ctx.fillStyle = "#00d4b6";
    ctx.fill();

    // Темний сектор ризику
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, rotRad - Math.PI / 2 + winRad, rotRad - Math.PI / 2 + Math.PI * 2);
    ctx.closePath();
    ctx.fillStyle = "#1b2434";
    ctx.fill();

    // Внутрішнє кільце та відсоток по центру
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.66, 0, Math.PI * 2);
    ctx.fillStyle = "#0b0f17";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.stroke();

    ctx.fillStyle = "#f5b400";
    ctx.font = "800 20px Inter, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(chance.toFixed(1) + "%", cx, cy - 6);

    ctx.fillStyle = "#8b9bb4";
    ctx.font = "700 10px Inter, system-ui, sans-serif";
    ctx.fillText("1 → 1 CHANCE", cx, cy + 14);
  }

  function spinUpgradeWheel(options) {
    var opts = options || {};
    var canvasEl = opts.canvasEl || null;
    var chance = calcChancePercent(opts.sourcePrice, opts.targetPrice);
    var roll = Math.random() * 100;
    var success = roll <= chance;

    var baseSpins = 5 * 360;
    var targetAngle = success
      ? (roll / 100) * 360 * 0.6
      : (chance / 100) * 360 + ((100 - roll) / Math.max(1, 100 - chance)) * 360 * 0.7;
    var finalAngle = baseSpins + targetAngle;

    if (!canvasEl) {
      if (typeof opts.onComplete === "function") {
        opts.onComplete({ success: success, chance: chance, roll: roll });
      }
      return;
    }

    var duration = 1800;
    var start = performance.now();

    function step(now) {
      var progress = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - progress, 3);
      drawWheel(canvasEl, chance, eased * finalAngle);
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        drawWheel(canvasEl, chance, finalAngle % 360);
        if (typeof opts.onComplete === "function") {
          opts.onComplete({ success: success, chance: chance, roll: roll });
        }
      }
    }

    requestAnimationFrame(step);
  }

  window.XAVRR_UPGRADE_WHEEL = {
    getCatalog: getCatalog,
    calcChancePercent: calcChancePercent,
    drawWheel: drawWheel,
    spin: spinUpgradeWheel,
    makeSerial: makeSerial
  };
})();
