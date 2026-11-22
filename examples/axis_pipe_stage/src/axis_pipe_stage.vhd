library ieee;
use ieee.std_logic_1164.all;

entity axis_pipe_stage is
  generic (DATA_W : positive := 8);
  port (
    clk             : in  std_logic;
    axis_in_tready  : out std_logic;
    axis_in_tvalid  : in  std_logic;
    axis_in_tdata   : in  std_logic_vector(DATA_W - 1 downto 0);
    axis_out_tready : in  std_logic;
    axis_out_tvalid : out std_logic;
    axis_out_tdata  : out std_logic_vector(DATA_W - 1 downto 0)
  );
end entity;

architecture rtl of axis_pipe_stage is
  signal v : std_logic := '0';
  signal d : std_logic_vector(DATA_W - 1 downto 0) := (others => '0');
begin
  axis_in_tready <= (not v) or axis_out_tready;

  process (clk)
  begin
    if rising_edge(clk) then
      if (not v) = '1' or axis_out_tready = '1' then
        v <= axis_in_tvalid;
        if axis_in_tvalid = '1' then
          d <= axis_in_tdata;
        end if;
      end if;
    end if;
  end process;

  axis_out_tvalid <= v;
  axis_out_tdata  <= d;
end architecture;
