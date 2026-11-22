--------------------------------------------------------------------------------
--
--! @file    top_adder_basic_tb.vhd
--! @brief   Generated testbench for top_adder (wavetb).
--! @date    22/11/2026
--! @details Self-checking testbench generated from WaveJSON. Do not edit by hand.
--
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity top_adder_basic_tb is
end entity; -- top_adder_basic_tb

architecture test of top_adder_basic_tb is
    constant CLK_PERIOD : time := 10000 ps;

    signal clk : std_logic := '1';
    signal a : std_logic_vector(7 downto 0) := (others => 'X');
    signal b : std_logic_vector(7 downto 0) := (others => 'X');
    signal sum : std_logic_vector(8 downto 0);
    signal na : std_logic_vector(7 downto 0);

    component top_adder is
        port (
            clk : in std_logic;
            a : in std_logic_vector(7 downto 0);
            b : in std_logic_vector(7 downto 0);
            sum : out std_logic_vector(8 downto 0);
            na : out std_logic_vector(7 downto 0)
        );
    end component;

begin

    UUT : top_adder
        port map (
            clk => clk,
            a => a,
            b => b,
            sum => sum,
            na => na
        );

    clk <= not clk after CLK_PERIOD / 2;

    process
        variable errors : natural := 0;
        variable cycle  : natural := 0;

        procedure check_cycle (
            constant a_value : in std_logic_vector(7 downto 0);
            constant b_value : in std_logic_vector(7 downto 0);
            constant sum_value : in std_logic_vector(8 downto 0);
            constant na_value : in std_logic_vector(7 downto 0)
        ) is
        begin
            a <= a_value;
            b <= b_value;
            wait until rising_edge(clk);
            if sum_value /= (sum_value'range => 'X') then
                if sum /= sum_value then
                    errors := errors + 1;
                    report "cycle " & integer'image(cycle) & ": sum - expected '" & to_string(sum_value) &
                        "' got '" & to_string(sum) & "'" severity error;
                end if;
            end if;
            if na_value /= (na_value'range => 'X') then
                if na /= na_value then
                    errors := errors + 1;
                    report "cycle " & integer'image(cycle) & ": na - expected '" & to_string(na_value) &
                        "' got '" & to_string(na) & "'" severity error;
                end if;
            end if;
            cycle := cycle + 1;
        end procedure check_cycle;

    begin
        -- Test: basic

        -- Cycle 0.
        check_cycle (
            a_value => std_logic_vector(to_unsigned(16#3#, a'length)),
            b_value => std_logic_vector(to_unsigned(16#4#, b'length)),
            sum_value => "XXXXXXXXX",
            na_value => "XXXXXXXX"
        );

        -- Cycle 1.
        check_cycle (
            a_value => std_logic_vector(to_unsigned(16#3#, a'length)),
            b_value => std_logic_vector(to_unsigned(16#4#, b'length)),
            sum_value => std_logic_vector(to_unsigned(16#7#, sum'length)),
            na_value => std_logic_vector(to_unsigned(16#FC#, na'length))
        );

        -- Cycle 2.
        check_cycle (
            a_value => std_logic_vector(to_unsigned(16#FF#, a'length)),
            b_value => std_logic_vector(to_unsigned(16#1#, b'length)),
            sum_value => std_logic_vector(to_unsigned(16#7#, sum'length)),
            na_value => std_logic_vector(to_unsigned(16#FC#, na'length))
        );

        -- Cycle 3.
        check_cycle (
            a_value => "XXXXXXXX",
            b_value => "XXXXXXXX",
            sum_value => std_logic_vector(to_unsigned(16#100#, sum'length)),
            na_value => std_logic_vector(to_unsigned(16#0#, na'length))
        );

        -- Cycle 4.
        check_cycle (
            a_value => "XXXXXXXX",
            b_value => "XXXXXXXX",
            sum_value => "XXXXXXXXX",
            na_value => "XXXXXXXX"
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
