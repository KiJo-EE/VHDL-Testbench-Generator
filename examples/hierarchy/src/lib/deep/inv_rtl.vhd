-- Architektur bewusst in eigener Datei (Entity steht in inv.vhd)
library ieee;
use ieee.std_logic_1164.all;

architecture rtl of inv is
begin
  y <= not x;
end architecture;
