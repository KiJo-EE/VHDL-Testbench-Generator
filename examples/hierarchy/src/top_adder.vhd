-- Top-Modul: instanziiert adder (per "entity work.") und inv (per Component)
-- aus Unterordnern. WaveTB findet beide automatisch.
library ieee;
use ieee.std_logic_1164.all;

entity top_adder is
  port (
    clk : in  std_logic;
    a   : in  std_logic_vector(7 downto 0);
    b   : in  std_logic_vector(7 downto 0);
    sum : out std_logic_vector(8 downto 0);
    na  : out std_logic_vector(7 downto 0)
  );
end entity;

architecture rtl of top_adder is
  component inv is
    port (x : in std_logic_vector(7 downto 0); y : out std_logic_vector(7 downto 0));
  end component;

  signal sum_c : std_logic_vector(8 downto 0);
  signal inv_c : std_logic_vector(7 downto 0);
begin
  u_add : entity work.adder
    port map (a => a, b => b, s => sum_c);

  u_inv : inv
    port map (x => a, y => inv_c);

  process (clk)
  begin
    if rising_edge(clk) then
      sum <= sum_c;
      na  <= inv_c;
    end if;
  end process;
end architecture;
