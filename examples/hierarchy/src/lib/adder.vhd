library ieee;
use ieee.std_logic_1164.all;
use work.util_pkg.all;

entity adder is
  port (
    a : in  std_logic_vector(7 downto 0);
    b : in  std_logic_vector(7 downto 0);
    s : out std_logic_vector(8 downto 0)
  );
end entity;

architecture rtl of adder is
begin
  s <= add9(a, b);
end architecture;
