# Security Policy

## Supported Versions

Khuzdul is currently in Alpha. At this time, only the latest release on the `main` branch is officially supported for security updates. 

| Version | Supported          |
| ------- | ------------------ |
| v1.x.x  | ❌ (Not yet released) |
| v0.x.x  | ✅                 |

## Threat Model & Scope

Khuzdul is a zero-abstraction systems tool frequently used for exploit development and shellcode generation. Therefore, generating "malicious" binaries is an intended use case of this software. 

**What IS considered a security vulnerability:**
* A specially crafted `.asm` file that causes Khuzdul to execute arbitrary code on the host machine *during the compilation process*.
* Path traversal vulnerabilities (e.g., manipulating input paths to read or overwrite arbitrary files on the host system).
* Denial of Service (DoS) attacks causing the compiler to consume infinite resources or crash the host machine through extreme memory exhaustion.

**What is NOT considered a security vulnerability (Please report these as standard Issues):**
* Khuzdul generating malformed or incorrect x86-64 machine bytes.
* Khuzdul successfully compiling a malicious payload (this is working as intended).
* Standard compilation crashes (e.g., unhandled Python exceptions) resulting from invalid syntax.

## Reporting a Vulnerability

We take the security of our compiler pipeline seriously. If you discover a vulnerability that falls within the scope defined above, **please do not open a public issue.** 

Instead, please report the vulnerability using one of the following methods:

1. **GitHub Security Advisories:** Navigate to the "Security" tab of this repository and click "Report a vulnerability" to open a private advisory draft.
2. **Email:** Send a detailed report directly to [this](39882449+mihinN@users.noreply.github.com).

### What to include in your report:
* A descriptive summary of the vulnerability.
* The exact version of Khuzdul and Python you are using.
* A minimal, reproducible `.asm` file or script that triggers the vulnerability.
* Steps to reproduce the issue.

### Response Timeline
You can expect an initial acknowledgment of your report within **48 hours**. If the vulnerability is verified, we will work with you to patch the issue, assign a CVE (if applicable), and publicly credit you for the discovery upon the release of the patch.
