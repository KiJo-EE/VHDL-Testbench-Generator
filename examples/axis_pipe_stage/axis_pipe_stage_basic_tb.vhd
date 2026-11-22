--------------------------------------------------------------------------------
--
--! @file    axis_pipe_stage_basic_tb.vhd
--! @brief   Generated testbench for axis_pipe_stage (wavetb).
--! @date    22/11/2026
--! @details Self-checking testbench generated from WaveJSON. Do not edit by hand.
--
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity axis_pipe_stage_basic_tb is
end entity; -- axis_pipe_stage_basic_tb

architecture test of axis_pipe_stage_basic_tb is
    constant CLK_PERIOD : time := 10000 ps;

    signal clk : std_logic := '1';
    signal axis_in_tready : std_logic;
    signal axis_in_tvalid : std_logic := '0';
    signal axis_in_tdata : std_logic_vector(7 downto 0) := (others => 'X');
    signal axis_out_tready : std_logic := '0';
    signal axis_out_tvalid : std_logic;
    signal axis_out_tdata : std_logic_vector(7 downto 0);

    component axis_pipe_stage is
        port (
            clk : in std_logic;
            axis_in_tready : out std_logic;
            axis_in_tvalid : in std_logic;
            axis_in_tdata : in std_logic_vector(7 downto 0);
            axis_out_tready : in std_logic;
            axis_out_tvalid : out std_logic;
            axis_out_tdata : out std_logic_vector(7 downto 0)
        );
    end component;

begin

    UUT : axis_pipe_stage
        port map (
            clk => clk,
            axis_in_tready => axis_in_tready,
            axis_in_tvalid => axis_in_tvalid,
            axis_in_tdata => axis_in_tdata,
            axis_out_tready => axis_out_tready,
            axis_out_tvalid => axis_out_tvalid,
            axis_out_tdata => axis_out_tdata
        );

    clk <= not clk after CLK_PERIOD / 2;

    process
        variable errors : natural := 0;
        variable cycle  : natural := 0;

        procedure check_cycle (
            constant axis_in_tready_value : in std_logic;
            constant axis_in_tvalid_value : in std_logic;
            constant axis_in_tdata_value : in std_logic_vector(7 downto 0);
            constant axis_out_tready_value : in std_logic;
            constant axis_out_tvalid_value : in std_logic;
            constant axis_out_tdata_value : in std_logic_vector(7 downto 0)
        ) is
        begin
            axis_in_tvalid <= axis_in_tvalid_value;
            axis_in_tdata <= axis_in_tdata_value;
            axis_out_tready <= axis_out_tready_value;
            wait until rising_edge(clk);
            if axis_in_tready_value /= 'X' then
                if axis_in_tready /= axis_in_tready_value then
                    errors := errors + 1;
                    report "cycle " & integer'image(cycle) & ": axis_in_tready - expected '" & to_string(axis_in_tready_value) &
                        "' got '" & to_string(axis_in_tready) & "'" severity error;
                end if;
            end if;
            if axis_out_tvalid_value /= 'X' then
                if axis_out_tvalid /= axis_out_tvalid_value then
                    errors := errors + 1;
                    report "cycle " & integer'image(cycle) & ": axis_out_tvalid - expected '" & to_string(axis_out_tvalid_value) &
                        "' got '" & to_string(axis_out_tvalid) & "'" severity error;
                end if;
            end if;
            if axis_out_tdata_value /= (axis_out_tdata_value'range => 'X') then
                if axis_out_tdata /= axis_out_tdata_value then
                    errors := errors + 1;
                    report "cycle " & integer'image(cycle) & ": axis_out_tdata - expected '" & to_string(axis_out_tdata_value) &
                        "' got '" & to_string(axis_out_tdata) & "'" severity error;
                end if;
            end if;
            cycle := cycle + 1;
        end procedure check_cycle;

    begin
        -- Test: basic

        -- Cycle 0.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '0',
            axis_in_tdata_value => "XXXXXXXX",
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '0',
            axis_out_tdata_value => "XXXXXXXX"
        );

        -- Cycle 1.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '1',
            axis_in_tdata_value => std_logic_vector(to_unsigned(16#AA#, axis_in_tdata'length)),
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '0',
            axis_out_tdata_value => "XXXXXXXX"
        );

        -- Cycle 2.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '1',
            axis_in_tdata_value => std_logic_vector(to_unsigned(16#5F#, axis_in_tdata'length)),
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '1',
            axis_out_tdata_value => std_logic_vector(to_unsigned(16#AA#, axis_out_tdata'length))
        );

        -- Cycle 3.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '0',
            axis_in_tdata_value => "XXXXXXXX",
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '1',
            axis_out_tdata_value => std_logic_vector(to_unsigned(16#5F#, axis_out_tdata'length))
        );

        -- Cycle 4.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '1',
            axis_in_tdata_value => std_logic_vector(to_unsigned(16#6B#, axis_in_tdata'length)),
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '0',
            axis_out_tdata_value => "XXXXXXXX"
        );

        -- Cycle 5.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '0',
            axis_in_tdata_value => "XXXXXXXX",
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '1',
            axis_out_tdata_value => std_logic_vector(to_unsigned(16#6B#, axis_out_tdata'length))
        );

        -- Cycle 6.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '0',
            axis_in_tdata_value => "XXXXXXXX",
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '0',
            axis_out_tdata_value => "XXXXXXXX"
        );

        -- Cycle 7.
        check_cycle (
            axis_in_tready_value => '1',
            axis_in_tvalid_value => '0',
            axis_in_tdata_value => "XXXXXXXX",
            axis_out_tready_value => '1',
            axis_out_tvalid_value => '0',
            axis_out_tdata_value => "XXXXXXXX"
        );

        if errors = 0 then
            report "TEST PASSED: basic";
            finish;
        else
            report "TEST FAILED: " & integer'image(errors) & " mismatch(es) in basic" severity failure;
        end if;
        wait;
    end process;

end architecture; -- test
