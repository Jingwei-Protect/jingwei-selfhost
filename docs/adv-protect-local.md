# Optional AdvProtect (local / self-host)

Not on the official website. Not on the Protect page.

## Disclaimer

We ran **multiple rounds** of tests against Doubao and similar closed-source editors. This class of adversarial perturbation has a **low success rate** there and often shows no visible protection. Experimental; may help some open diffusion pipelines; **not a promise against Doubao or Jimeng.**

我们用豆包等常见闭源改图工具做过**多轮实测**。这类对抗扰动在这些工具上成功率很低，经常几乎看不出防护。实验性选项，可能对部分开源扩散模型有效，**不能当作防豆包、即梦的承诺。**

## Docker

Default:

```bash
docker compose up --build
```

AdvProtect (stop the default stack first — same port 8080):

```bash
docker compose down
docker compose -f compose.yaml -f compose.adv.yaml up --build
```

Then open `http://127.0.0.1:8080/adv-protect`. The nav link appears only when `ENABLE_ADV_PROTECT=1`.

Without Docker: `pip install -r requirements-adv.txt`, set `ENABLE_ADV_PROTECT=1`, restart the API.
