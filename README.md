# Light don go

When NEPA takes light, and before anyone starts the generator, your laptop tells you to go outside, then gets out of the way.

- **Detects the cut:** the laptop drops to battery for 30 s or more (no inverter in this house).
- **Works with the router dead:** the forecast is saved while power is on; after the cut nothing touches the network.
- **Code decides, Gemma phrases:** rules compute sunset (NOAA formula, offline), the dry window and ₦ saved, and write the facts line. A local open-weight Gemma writes only the nudge, and a guard rejects it if it has any number, more than 20 words, or mentions light/the generator. One retry, then a fixed sentence.

```
Light don go. Rain fit start around 17:00: you get 110 minutes. Hold the gen: ₦1,500 saved every hour e rest.
Abeg shut that laptop, go walk to the junction buy roasted plantain and fish now.
Close the laptop. Go outside.
```

## Run

```bash
pip install -e ".[test]"
ollama pull gemma4:e2b-it-qat
ldg refresh                      # save forecast (needs internet)
ldg watch                        # wait for a real outage
ldg simulate --at 15:10 --battery 63 --forecast tests/fixtures/demo_dry_then_rain.json
python -m pytest -q
```

Every event goes to `logs/outages.jsonl`.

## Model timing (2026-10-08)

`gemma4:e2b-it-qat` (4.3 GB) via Ollama 0.35.0 on an i5-1135G7, CPU only, 15.7 GB RAM:
cold 14.1 s (7.9 s load), warm 3.6–4.0 s, about 15–20 tokens/s. `ldg watch` warms the model at start.
Script: `bench/time_model.py`.
