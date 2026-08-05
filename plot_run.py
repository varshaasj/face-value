import matplotlib.pyplot as plt

def plot_run(history, trades, out="figures/run.png"):
    NA = float("nan")

    t    = [h[0] for h in history]
    fair = [h[1] for h in history]
    bid  = [h[2] if h[2] is not None else NA for h in history]
    ask  = [h[3] if h[3] is not None else NA for h in history]

    mid    = [(b + a) / 2 for b, a in zip(bid, ask)]
    spread = [a - b for b, a in zip(bid, ask)]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(13, 7), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]}
    )

    # trades as a faint scatter underneath everything
    if trades:
        ax1.scatter([tr[0] for tr in trades], [tr[1] for tr in trades],
                    s=4, alpha=0.12, color="#888", label="trades", zorder=1)

    ax1.plot(t, fair, lw=2, color="#111", label="fair value (truth)", zorder=3)
    ax1.plot(t, mid,  lw=1, color="#c0392b", label="mid (belief)", zorder=2)
    ax1.fill_between(t, bid, ask, alpha=0.18, color="#c0392b",
                     label="bid–ask", zorder=0)

    ax1.set_ylabel("price (cents)")
    ax1.legend(loc="upper left", frameon=False)
    ax1.set_title("Face Value — fair value vs. the market's belief")

    ax2.plot(t, spread, lw=1, color="#2c3e50")
    ax2.set_ylabel("spread")
    ax2.set_xlabel("time")
    ax2.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(out, dpi=140)
    print(f"saved {out}")


#Made by Claude for visualizing