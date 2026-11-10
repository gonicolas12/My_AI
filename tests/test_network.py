"""
Client HTTP de Hugging Face réglé par core/network.py.

configure_http_backend (huggingface_hub 0.x, sur requests) n'existe plus en 1.x
(httpx) ni en 2.x (httpx2), que tire transformers 5.x : son import échouait sans
bruit, et la vérification TLS de config.yaml (bundle CA d'entreprise, ou
allow_insecure_ssl) ne s'appliquait plus aux téléchargements des modèles. Les
poids des modèles passent en plus par hf-xet, dont le client ignore ce réglage :
il est coupé quand un réglage TLS est donné. Le Mac Intel, resté en
transformers 4.x, garde huggingface_hub 0.x.
"""

import os
import ssl
import sys
import types

import certifi
import huggingface_hub
import pytest
import requests

from core import network

# pylint: disable=protected-access


class _Client:
    """Client httpx simulé : retient les réglages reçus."""

    def __init__(self, **options):
        self.options = options
        self.event_hooks = options.get("event_hooks", {"request": ["hook hors ligne"], "response": []})
        self.follow_redirects = options.get("follow_redirects", True)
        self.timeout = options.get("timeout", "délai du Hub")


@pytest.fixture(name="xet_env")
def _xet_env(monkeypatch):
    """HF_HUB_DISABLE_XET rétabli après le test (le code l'écrit dans os.environ)."""
    monkeypatch.setenv("HF_HUB_DISABLE_XET", "0")


@pytest.fixture(name="hub")
def _hub(monkeypatch, xet_env):  # pylint: disable=unused-argument
    """huggingface_hub 1.x/2.x simulé : client par défaut, fabriques reçues."""
    hub = types.SimpleNamespace(factories=[], default=_Client(),
                                constants=types.SimpleNamespace(HF_HUB_DISABLE_XET=False))
    hub.get_session = lambda: hub.default
    hub.set_client_factory = hub.factories.append
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    return hub


def _configure(verify):
    result = {"warnings": []}
    network._configure_huggingface_backend("", "", "", verify, result)
    return result


def _xet_disabled(hub):
    return hub.constants.HF_HUB_DISABLE_XET, os.environ["HF_HUB_DISABLE_XET"]


def test_ca_bundle_reaches_the_hub_client(hub):
    assert _configure(certifi.where()) == {"warnings": [], "huggingface_backend_configured": True}
    (factory,) = hub.factories
    client = factory()
    # Même client que celui du Hub (hook du mode hors ligne, redirections, délai)
    assert {name: client.options[name] for name in ("event_hooks", "follow_redirects", "timeout")} == {
        "event_hooks": {"request": ["hook hors ligne"], "response": []},
        "follow_redirects": True,
        "timeout": "délai du Hub",
    }
    tls = client.options["verify"]
    assert isinstance(tls, ssl.SSLContext) and tls.verify_mode == ssl.CERT_REQUIRED
    assert tls.get_ca_certs()
    # Poids des modèles : par ce client, pas par hf-xet qui ignorerait le bundle
    assert _xet_disabled(hub) == (True, "1")


def test_insecure_ssl_reaches_the_hub_client(hub):
    _configure(False)
    (factory,) = hub.factories
    assert factory().options["verify"] is False
    assert _xet_disabled(hub) == (True, "1")


def test_without_tls_setting_the_hub_keeps_its_own_clients(hub):
    # Proxys et magasin du système : le client du Hub et hf-xet les suivent seuls
    assert _configure(None) == {"warnings": [], "huggingface_backend_configured": True}
    assert not hub.factories
    assert _xet_disabled(hub) == (False, "0")


def test_unreadable_ca_bundle_does_not_stop_the_launch(hub, tmp_path):
    bundle = tmp_path / "ca.pem"
    bundle.write_text("pas un certificat", encoding="utf-8")
    result = _configure(str(bundle))
    assert result["huggingface_backend_configured"] is False
    assert "Hugging Face" in result["warnings"][0]
    assert not hub.factories
    assert _xet_disabled(hub) == (False, "0")


def test_hub_0x_keeps_its_requests_backend(monkeypatch):
    backends = []
    hub = types.SimpleNamespace(configure_http_backend=lambda backend_factory: backends.append(backend_factory))
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    result = {"warnings": []}
    network._configure_huggingface_backend("http://proxy:3128", "", "", certifi.where(), result)
    assert result["huggingface_backend_configured"] is True
    session = backends[0]()
    assert isinstance(session, requests.Session)
    assert session.proxies == {"http": "http://proxy:3128"} and session.verify == certifi.where()


@pytest.mark.skipif(not hasattr(huggingface_hub, "set_client_factory"), reason="huggingface_hub 0.x")
def test_real_hub_client_still_blocks_requests_offline(monkeypatch, xet_env):  # pylint: disable=unused-argument
    """Le client recopié garde le hook qui refuse toute requête hors ligne."""
    from huggingface_hub import constants  # pylint: disable=import-outside-toplevel
    from huggingface_hub.errors import OfflineModeIsEnabled  # pylint: disable=import-outside-toplevel

    factories = []
    monkeypatch.setattr(huggingface_hub, "set_client_factory", factories.append)
    monkeypatch.setattr(constants, "HF_HUB_DISABLE_XET", False)
    assert _configure(certifi.where())["huggingface_backend_configured"] is True
    assert constants.HF_HUB_DISABLE_XET is True
    client = factories[0]()
    assert type(client) is type(huggingface_hub.get_session()) and client.follow_redirects
    monkeypatch.setattr(constants, "HF_HUB_OFFLINE", True)
    with pytest.raises(OfflineModeIsEnabled):
        client.get("https://huggingface.co/api/models/cross-encoder/ms-marco-MiniLM-L-6-v2")
