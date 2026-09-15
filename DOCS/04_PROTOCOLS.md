# Mira Protocols

This document drafts the shared message envelope and the private-house
conversation model used by Mira and PyGDO connectors.

## Inter-lifeform message envelope

The human-readable wire form is a routing prefix, a fully-qualified username,
and an unchanged message payload:

```text
1#<channel> <fq_username> <PAYLOAD>
2##<deprecated-or-unofficial-channel> <fq_username> <PAYLOAD>
3###<house-room> <fq_username> <PAYLOAD>
```

The leading number describes the precedence of the marker and is explanatory;
on the wire the markers are one, two, or three hash characters:

```text
#<channel> <fq_username> <PAYLOAD>
##<deprecated-or-unofficial-channel> <fq_username> <PAYLOAD>
###<house-room> <fq_username> <PAYLOAD>
```

Examples:

```text
#wechall gizmore{wc} hi mira
##irc_wechall gizmore{irc1} a deprecated or unofficial IRC message
###House_LivingRoom gizmore{bash} Hello Mira
###Mogwai_Dev mira{ws} file-change event received
```

Fields are deliberately simple:

- `#` identifies an official inter-lifeform channel, such as IRC, Telegram,
  Signal, Discord, or another supported channel.
- `##` identifies the same kind of channel when it is deprecated, unofficial,
  or otherwise lower-confidence.
- `###` identifies a physical or house-system room, using a stable name such as
  `###House_Room`.
- `fq_username` has the form `username{connector-or-server}`, for example
  `gizmore{irc1}`, `gizmore{bash}`, `gizmore{ws}`, or `gizmore{wc}`.
- `PAYLOAD` is the message body and must remain intact at the transport
  boundary.

The envelope is a routing and conversation format, not an authorization token.
A protocol-correct message may be answered normally, but sensitive, destructive,
privileged, or externally visible actions still require separate authorization.

## Mira chat language hint

When a routed message addresses Mira, the private local hand-off starts with a
language hint derived from `GDO_Channel.chan_language`:

```text
$chat --lang=de
2026-09-16 12:00:00.000000 #53 gizmore{rizon} mira, hallo
```

`--lang` is a lower-case ISO-639-1 code and defaults to `en` when no channel
is available or its setting is invalid. It is metadata for Mira's reply
language; it does not alter the IBDES records that follow.

## Unprefixed messages

Parsers inspect messages in this order:

1. A message beginning with `###`, `##`, or `#` is a room/channel message.
2. A message beginning with an `fq_username` is a possible private message.
   The connector may deliver it privately after validating the sender and
   destination context.
3. A message beginning with neither a channel marker nor an `fq_username` is
   an **unframed payload**. It may be connector-local metadata, a system/event
   record, or malformed input; it has no trustworthy sender or routing scope.
   Do not treat it as an authenticated user message or execute it as a command.

Connectors may wrap an unframed payload with its observed source and a stable
event identifier, but must not invent a human sender. If the connector cannot
classify it, retain it for diagnostics or reject it according to its transport
policy.

## House-system rooms

### Purpose

A house system is a private, local collection of rooms for people, agents,
devices, and services sharing one physical or trusted digital environment. It
is a conversation space first: humans can ask questions, agents can report
state, and services can announce events without pretending that every message
is a command.

### Room naming

Use a stable slug after `###`, for example:

```text
###HQ2_LivingRoom
###HQ2_Workshop
###Mogwai_Dev
```

Room names should not contain credentials, personal secrets, or transient
session identifiers. Display names may be maintained separately from the
stable room slug.

### Participants

A participant can be a human, an AI, a connector, or a device. The sender
identity and server instance remain explicit so that a bridged message does
not silently become a different identity.

```text
###House_LivingRoom marion{irc1} Is gizmore around?
###Mogwai_Dev mira{local} file-change event received
```

Bridges must preserve the original envelope and add provenance rather than
rewriting the sender. A room may route an answer to another connector, but it
must not leak private-room content into a public channel by default.

## Mail bridge

Local Postfix mail can use plus-addressing to preserve the source account and
category:

```text
mira+wechall@localhost
mira+linkuup@localhost
mira+gwf3+errors@localhost
mira+wechall+spam@localhost
```

The complete extension after the first `+` is meaningful. A mail connector may
normalize it to a safe queue slug such as `gwf3-errors`, while retaining the
original envelope recipient in metadata. Mail must enter a private queue before
it becomes a PyGDO conversation; no automatic external reply is implied.

## Routing rules

1. Parse and validate the envelope before dispatch.
2. Preserve sender, server, room, and payload as received.
3. Treat `###` content as private unless an explicit bridge authorizes release.
4. Deduplicate bridged events with a stable event identifier.
5. Keep transport-independent method logic in PyGDO; connectors only adapt the
   envelope and delivery mechanism.
6. Log the minimum technical metadata needed for debugging. Do not log full
   private payloads by default.

## Draft event shape

Internal connectors may normalize an envelope to a structure like:

```json
{
  "scope": "house",
  "room": "HQ2_LivingRoom",
  "user": "Marion",
  "connector": "irc1",
  "payload": "Hello Mira",
  "source": "tcp",
  "event_id": "connector-defined-stable-id"
}
```

The JSON shape is an internal adapter contract; the readable envelope remains
the interoperable human-facing form.
