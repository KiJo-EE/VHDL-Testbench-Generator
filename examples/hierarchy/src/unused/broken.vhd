-- Wird von top_adder nicht gebraucht und darf deshalb nie compiliert werden
-- (enthaelt absichtlich einen Syntaxfehler).
entity broken is
  port ( x : in bit
end entity;
