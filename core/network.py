"""
Utilitaires d'initialisation reseau.

Objectifs:
- Prendre en charge les proxys standards sans configuration specifique.
- Gerer l'interception TLS d'entreprise via un bundle CA personnalise.
- Conserver un comportement sur par defaut (verification SSL activee).
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from typing import Any, Dict, Optional

_NETWORK_CONFIGURED = False
_LAST_RESULT: Dict[str, Any] = {}


def _as_bool(value: Any, default: bool) -> bool:
    """Convertit une valeur en booléen avec des règles de parsing communes."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _as_str(value: Any) -> str:
    """Convertit une valeur en chaîne de caractères, ou retourne une chaîne vide si la valeur est None ou vide après conversion."""
    if value is None:
        return ""
    return str(value).strip()


def _load_network_config() -> Dict[str, Any]:
    """Charge la section de configuration réseau depuis config.yaml, ou retourne un dict vide en cas d'erreur."""
    try:
        from core.config import get_config  # pylint: disable=import-outside-toplevel

        section = get_config().get_section("network") or {}
        return section if isinstance(section, dict) else {}
    except Exception:
        return {}


def _set_env_pair(key: str, value: str, prefer_environment: bool) -> bool:
    """Met une variable d'environnement en respectant la priorité de l'environnement existant si prefer_environment est True. Retourne True si la variable a été définie ou mise à jour."""
    if not value:
        return False

    lower_key = key.lower()
    existing = os.environ.get(key) or os.environ.get(lower_key)

    if prefer_environment and existing:
        return False

    os.environ[key] = value
    os.environ[lower_key] = value
    return True


def _get_env(key: str) -> str:
    """Retourne la valeur d'une variable d'environnement en vérifiant à la fois la casse originale et la casse inférieure, ou une chaîne vide si aucune n'est définie."""
    return os.environ.get(key) or os.environ.get(key.lower(), "")


def _resolve_existing_file(path_value: str) -> Optional[str]:
    """Résout et valide un chemin de fichier. Retourne le chemin absolu normalisé."""
    if not path_value:
        return None

    expanded = os.path.expandvars(os.path.expanduser(path_value))
    candidate = Path(expanded)

    if candidate.is_file():
        return str(candidate.resolve())
    return None


def _configure_huggingface_backend(
    http_proxy: str,
    https_proxy: str,
    all_proxy: str,
    verify: Optional[str | bool],
    result: Dict[str, Any],
) -> None:
    """
    Configure le backend HTTP de HuggingFace pour respecter les paramètres de proxy et de vérification TLS.
    Modifie le résultat avec une clé "huggingface_backend_configured" indiquant si
    """
    try:
        import requests  # pylint: disable=import-outside-toplevel
        from huggingface_hub import (  # pylint: disable=import-outside-toplevel
            configure_http_backend,
        )
    except Exception:
        result["huggingface_backend_configured"] = False
        return

    def _backend_factory() -> requests.Session:
        session = requests.Session()

        # Keep explicit proxies only when provided.
        proxies = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        if all_proxy:
            proxies.setdefault("http", all_proxy)
            proxies.setdefault("https", all_proxy)
        if proxies:
            session.proxies.update(proxies)

        if verify is not None:
            session.verify = verify

        return session

    configure_http_backend(backend_factory=_backend_factory)
    result["huggingface_backend_configured"] = True


def configure_network_environment(force: bool = False) -> Dict[str, Any]:
    """
    Configure l'environnement réseau pour les appels HTTP sortants, en respectant la configuration définie dans config.yaml. 
    Si force est True, reconfigure même si l'environnement a déjà été configuré. Retourne un dict avec les détails de la configuration appliquée et les avertissements éventuels.
    """
    global _NETWORK_CONFIGURED, _LAST_RESULT

    if _NETWORK_CONFIGURED and not force:
        return dict(_LAST_RESULT)

    cfg = _load_network_config()
    proxy_cfg = cfg.get("proxy") if isinstance(cfg.get("proxy"), dict) else {}
    tls_cfg = cfg.get("tls") if isinstance(cfg.get("tls"), dict) else {}

    prefer_environment = _as_bool(
        cfg.get("prefer_environment", proxy_cfg.get("prefer_environment", True)),
        True,
    )

    proxy_url = _as_str(cfg.get("proxy_url", proxy_cfg.get("url", "")))
    http_proxy = _as_str(cfg.get("http_proxy", proxy_cfg.get("http", ""))) or proxy_url
    https_proxy = _as_str(cfg.get("https_proxy", proxy_cfg.get("https", ""))) or proxy_url
    all_proxy = _as_str(cfg.get("all_proxy", proxy_cfg.get("all", "")))
    no_proxy = _as_str(cfg.get("no_proxy", proxy_cfg.get("no_proxy", "")))

    ca_bundle_value = _as_str(cfg.get("ca_bundle", tls_cfg.get("ca_bundle", "")))
    use_system_truststore = _as_bool(
        cfg.get(
            "use_system_truststore",
            tls_cfg.get("use_system_truststore", True),
        ),
        True,
    )
    allow_insecure_ssl = _as_bool(
        cfg.get("allow_insecure_ssl", tls_cfg.get("allow_insecure_ssl", False)),
        False,
    )

    result: Dict[str, Any] = {
        "prefer_environment": prefer_environment,
        "proxy_env_applied": [],
        "warnings": [],
        "ca_bundle": "",
        "truststore_enabled": False,
        "allow_insecure_ssl": allow_insecure_ssl,
        "huggingface_backend_configured": False,
    }

    if _set_env_pair("HTTP_PROXY", http_proxy, prefer_environment):
        result["proxy_env_applied"].append("HTTP_PROXY")
    if _set_env_pair("HTTPS_PROXY", https_proxy, prefer_environment):
        result["proxy_env_applied"].append("HTTPS_PROXY")
    if _set_env_pair("ALL_PROXY", all_proxy, prefer_environment):
        result["proxy_env_applied"].append("ALL_PROXY")
    if _set_env_pair("NO_PROXY", no_proxy, prefer_environment):
        result["proxy_env_applied"].append("NO_PROXY")

    # Always avoid proxying localhost unless user explicitly configured it.
    if not _get_env("NO_PROXY"):
        _set_env_pair("NO_PROXY", "localhost,127.0.0.1,::1", prefer_environment=False)

    resolved_ca_bundle = _resolve_existing_file(ca_bundle_value)
    if resolved_ca_bundle:
        result["ca_bundle"] = resolved_ca_bundle
        for env_key in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "SSL_CERT_FILE"):
            _set_env_pair(env_key, resolved_ca_bundle, prefer_environment)
    elif ca_bundle_value:
        result["warnings"].append(
            f"network.ca_bundle introuvable: {ca_bundle_value}"
        )

    if use_system_truststore:
        try:
            context = ssl.create_default_context()
            context.load_default_certs()
            result["truststore_enabled"] = True
        except Exception:
            result["truststore_enabled"] = False

    hf_verify: Optional[str | bool] = None
    if resolved_ca_bundle:
        hf_verify = resolved_ca_bundle
    elif allow_insecure_ssl:
        hf_verify = False

    _configure_huggingface_backend(
        http_proxy=_get_env("HTTP_PROXY"),
        https_proxy=_get_env("HTTPS_PROXY"),
        all_proxy=_get_env("ALL_PROXY"),
        verify=hf_verify,
        result=result,
    )

    if allow_insecure_ssl:
        result["warnings"].append(
            "allow_insecure_ssl=true: verification TLS desactivee (non recommande en production)."
        )

    _NETWORK_CONFIGURED = True
    _LAST_RESULT = dict(result)
    return dict(result)


def build_network_error_help(error: Exception) -> str:
    """Retourne un message d'aide contextuel basé sur le type d'erreur réseau rencontrée."""
    message = str(error).lower()
    hints = []

    if any(token in message for token in ("certificate_verify_failed", "ssl", "tls")):
        hints.append(
            "Erreur TLS detectee: configurez network.ca_bundle (certificat racine du proxy) "
            "ou exportez REQUESTS_CA_BUNDLE/SSL_CERT_FILE."
        )
        hints.append(
            "Si le probleme persiste, fournissez explicitement network.ca_bundle avec votre certificat racine."
        )

    if any(token in message for token in ("proxy", "407", "tunnel", "forbidden")):
        hints.append(
            "Proxy detecte: configurez HTTP_PROXY/HTTPS_PROXY (ou network.http_proxy/network.https_proxy)."
        )
        hints.append(
            "Ajoutez localhost,127.0.0.1,::1 dans NO_PROXY pour ne pas casser les appels locaux (Ollama)."
        )

    if not hints:
        return ""

    return "\n".join(["   Aide reseau:"] + [f"   - {hint}" for hint in hints])
