# Phase 11C.3 — Temporal Consistency Analysis

**Status:** IMPLEMENTATION

## Purpose

Provide a deterministic, read-only analysis layer over the temporal
interval and precision representations introduced in Phase 11C.1 and
11C.2.

The purpose is to determine what the available temporal evidence actually
supports without treating uncertainty or overlap as contradiction.

## Design Principle

Temporal overlap is **not** automatically a contradiction.

For example:

- Evidence A: January 2024
- Evidence B: January 15, 2024

These assertions can both be true.

Likewise:

- Evidence A: sometime in 2024
- Evidence B: sometime in June 2024

does not establish that either assertion is false.

## Current Scope

The consistency layer:

- compares temporal intervals pairwise;
- preserves deterministic input ordering;
- exposes relationship and certainty;
- distinguishes definite relationships from indeterminate overlap;
- provides a report object;
- does not modify governed evidence.

## Deliberate Limitation

Plain temporal intervals alone cannot establish that two assertions are
mutually exclusive.

For example, two overlapping state intervals are not necessarily
contradictory.

Therefore this phase does **not** manufacture contradiction records from
ordinary overlap.

A future contradiction phase may introduce explicit semantic constraints
such as:

- mutually exclusive states;
- replacement/deactivation constraints;
- impossible ordering constraints;
- entity-specific lifecycle rules.

Only those constraints can establish a genuine temporal contradiction.

## Non-Goals

This phase does not:

- modify temporal evidence;
- revoke evidence;
- resolve entities;
- infer missing timestamps;
- create database records;
- change retrieval;
- change ranking;
- modify the UI;
- call an LLM;
- declare overlapping evidence contradictory.

## Governance

All results are derived from existing evidence and remain non-authoritative
until a later governed layer explicitly promotes a conclusion.
