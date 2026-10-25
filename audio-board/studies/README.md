# Studies

Analysis and design studies of the Seed3 carrier board. Each study has its own
folder with a README (question, method, results, caveats), the script that
produces its figures, and the figures themselves.

| Study | Question |
|---|---|
| [signal-path-response](signal-path-response/) | How much phase shift and delay does the carrier's analog circuitry add, with the Daisy treated as ideal? |

## Running the scripts

Python 3 with the packages in `requirements.txt`:

```bash
pip install -r studies/requirements.txt
python3 studies/signal-path-response/phase_response.py
```

Scripts write their figures next to themselves, so they can be run from any
directory. Re-run a study's script after changing component values on the board
and commit the regenerated figure together with the change.
