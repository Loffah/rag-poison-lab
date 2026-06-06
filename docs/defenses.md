# Defenses: naive vs hardened

The lab supports two modes. The interesting comparison is the delta between them.

- **naive** (default): documents are concatenated into the prompt as-is, with a permissive system prompt. Most attacks that can land, land.
- **hardened**: documents are wrapped in provenance-stamped `<doc>` tags, the system prompt instructs the model to treat tagged content as untrusted data, and retrieved content is sanitized at ingest.

The hardened mode applies several distinct mitigation classes. Each targets specific families; none depends on the model's alignment to hold the line, which is why they're useful in production regardless of which model you run.

## Instruction/data separation

Helps `direct_override`, `indirect_injection`, and (as their only hardened defense) `multi_hop`.

1. Retrieved content is wrapped in `<doc>...</doc>` tags.
2. A stricter system prompt tells the model to treat tagged content as **data, not instructions**, and to follow only the user message.

## Parser-layer ingest sanitization

Helps `markdown_exfil` and `hidden_text`. Applied to retrieved content before the model ever sees it:

3. Strips markdown image syntax (defeats `markdown_exfil`).
4. Removes zero-width characters, drops HTML comments, deletes invisible inline-styled elements (white-on-white, `font-size:0`), and neutralizes standalone base64 blobs.

This defeats four of the five `hidden_text` variants outright at ingest: the canary is removed entirely. The `zero_width_interleave` variant is *de-obfuscated* rather than deleted: stripping the invisible characters surfaces the instruction so the separation layer and a human auditor can act on it.

## Provenance / channel-impersonation neutralization

Helps `format_spoofing`.

5. Each `<doc>` is stamped with its `source` and an explicit `trust="untrusted"` attribute, and the hardened system prompt warns that untrusted content may imitate a trusted channel.
6. Tokens that impersonate a trusted message channel (`<system>`-style tags, faked prior assistant/tool turns) are neutralized at ingest so the spoof can't borrow authority.

This is the lab's stand-in for real source attestation. **Honest limitation:** header- and JSON-style spoofs (fake compliance stamps, fake tool-output blocks) have no clean structural token to strip and rely on the trust envelope alone.

## Tool authorization rule

Helps `tool_call_hijack`.

7. When tools are exposed, the hardened system prompt adds an authorization rule: sensitive tools may only be invoked to fulfill the user's explicit request, never because a retrieved document asks for it.

!!! warning "This is a behavioral cue, not an enforced gate"
    The lab does not execute tool calls, so it cannot *block* one. The honest production fix is an authorization layer with human-in-the-loop confirmation, outside the model. Hardened mode measures whether the rule changes the model's behavior.

## Reading the delta

The naive-vs-hardened delta is the architectural-mitigation demonstration. Against the current Claude family, naive-mode landings are already low (a small handful out of the corpus in a given run), so the hardened delta there is small and noisy. Against weaker or open-weight models, where naive landings are an order of magnitude higher, the delta is correspondingly larger, which is when the hardened mitigations earn their keep.
