import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wavetb.__main__ import main  # noqa: E402

sys.exit(main())
