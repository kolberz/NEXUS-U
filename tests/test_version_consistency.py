from nexus_u import __version__
from nexus_u.cli import build_parser


def test_cli_version_uses_package_version(capsys):
    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out.strip()
    assert output == f"nexus-u {__version__}"
