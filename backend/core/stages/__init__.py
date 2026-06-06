"""Pipeline stages — one stage is one independently testable, swappable unit.

  source   Stage 1  Ocean.io    seed -> lookalike companies
  prospect Stage 2  Prospeo     companies -> decision-makers + LinkedIn
  resolve  Stage 3  Eazyreach   LinkedIn -> verified work email
  send     Stage 4  Brevo       contacts -> outreach sent
"""
